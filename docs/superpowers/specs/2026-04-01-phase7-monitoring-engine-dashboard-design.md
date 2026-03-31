# Phase 7 監視エンジン + Streamlit ダッシュボード 設計仕様

**対象 Issue:** #38 取引・リスク監視エンジン実装、#35 Streamlit監視ダッシュボード実装  
**作成日:** 2026-04-01

---

## 1. 概要

Phase 7 コアとして、以下を実装する。

- `system_monitor.py` — CPU/メモリ/ディスク/プロセス生存/データ鮮度チェック
- `trade_monitor.py` — 注文滞留・約定異常価格検出
- `risk_monitor.py` — ドローダウン・ポジション上限監視
- `monitoring_engine.py` — 各 Monitor を束ねるポーリング統括
- `streamlit_dashboard.py` — Streamlit 監視 UI

既存の `monitoring_db.py`（MonitoringDB クラス・5テーブル）をデータ永続化層として利用する。

---

## 2. アーキテクチャ

```
src/kabusys/monitoring/
├── monitoring_db.py        # 既存 (済)
├── system_monitor.py       # NEW
├── trade_monitor.py        # NEW
├── risk_monitor.py         # NEW
├── monitoring_engine.py    # NEW
└── streamlit_dashboard.py  # NEW
```

**データフロー:**

```
[psutil / DuckDB / OrderRepository]
        ↓
[SystemMonitor / TradeMonitor / RiskMonitor]  ←── check_once()
        ↓
    MonitoringDB (SQLite: monitoring.db)
        ↑
[MonitoringEngine] — 60秒ポーリングで各 Monitor を呼び出す

[StreamlitDashboard] — MonitoringDB を直接 read（MonitoringEngine と独立）
```

**設計原則:**
- 各 Monitor は内部ループを持たない（`check_once()` のみ）→ テスト容易性確保
- `MonitoringEngine` が `while True` + `time.sleep(interval)` でポーリング管理
- Streamlit は `st.rerun(every=30)` で30秒自動リフレッシュ

---

## 3. SystemMonitor (`system_monitor.py`)

Monitoring.md § 3 の仕様に完全準拠。

### データクラス

```python
@dataclass
class SystemCheckResult:
    recorded_at: str          # ISO8601 UTC
    cpu_percent: float        # psutil.cpu_percent()
    memory_percent: float     # psutil.virtual_memory().percent
    disk_percent: float       # psutil.disk_usage("C:\\").percent
    process_ok: bool          # PID ファイル方式による Execution プロセス生存確認
    data_freshness_ok: bool   # 株価データが3日以内に更新済み
    stale_pid_detected: bool  # 異常終了 PID を検出・削除した場合 True
```

### クラス API

```python
class SystemMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: duckdb.DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
    ) -> None

    def check_once(self, today: date | None = None) -> SystemCheckResult
```

### PID ファイル方式（Monitoring.md § 3 準拠）

| 状態 | 判定 |
|---|---|
| PID ファイルなし | 未起動 or 正常終了（`process_ok=False`） |
| PID ファイルあり・プロセス生存 | 正常稼働（`process_ok=True`） |
| PID ファイルあり・プロセス死亡 | 異常終了 → stale PID 削除・`stale_pid_detected=True` |

### データ鮮度チェック

`DuckDBRepository.get_last_price_date()` を呼び出し、最終更新日が `today - 3日` より古い場合（または None）を `data_freshness_ok=False` とする。

### 書き込み

`check_once()` 内で `MonitoringDB.log_system_status()` を呼び出す。

---

## 4. TradeMonitor (`trade_monitor.py`)

Monitoring.md § 6 の仕様に準拠。

### データクラス

```python
@dataclass
class TradeCheckResult:
    logged_at: str
    stale_orders: list[str]    # 30分以上 Created/Sent/Accepted 状態の client_order_id
    anomaly_fills: list[str]   # 約定価格が参照価格 ±20% 超の client_order_id
```

### クラス API

```python
class TradeMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        stale_minutes: int = 30,
        price_anomaly_pct: float = 0.20,
    ) -> None

    def check_once(self, now: datetime | None = None) -> TradeCheckResult
```

### ロジック

- **注文滞留検出:** `trade_logs` テーブルから `state IN ('Created', 'Sent', 'Accepted')` の注文を取得し、`logged_at` から `stale_minutes` 分以上経過しているものを `stale_orders` に追加。
- **約定異常価格検出:** 同一 `client_order_id` の `price`（発注価格）と `Filled` イベントの `price` を比較し、乖離率が `price_anomaly_pct` 超の場合を `anomaly_fills` に追加。

### 書き込み

異常検出時のみ `MonitoringDB.log_risk_event()` に記録（`event_type="STALE_ORDER"` or `"PRICE_ANOMALY"`）。

---

## 5. RiskMonitor (`risk_monitor.py`)

Monitoring.md § 7 および RiskManagement.md の閾値に準拠。

### データクラス

```python
@dataclass
class RiskCheckResult:
    logged_at: str
    drawdown_pct: float
    drawdown_alert: bool        # drawdown_pct > dd_threshold (デフォルト 10%)
    position_count: int
    position_limit_alert: bool  # position_count > max_positions (デフォルト 10)
```

### クラス API

```python
class RiskMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        peak_value: float,        # ポートフォリオ最高値（外部から注入）
        max_positions: int = 10,
        dd_threshold: float = 0.10,
    ) -> None

    def check_once(self, now: datetime | None = None) -> RiskCheckResult
```

### ロジック

- **ドローダウン計算:** `dashboard` テーブルの `portfolio_value` を取得し、`(peak_value - portfolio_value) / peak_value` で計算。
- **ポジション数:** `positions` テーブルの行数をカウント。
- **アラート判定:** 閾値超過時に `MonitoringDB.log_risk_event()` に記録。

---

## 6. MonitoringEngine (`monitoring_engine.py`)

### クラス API

```python
class MonitoringEngine:
    def __init__(
        self,
        system_monitor: SystemMonitor,
        trade_monitor: TradeMonitor,
        risk_monitor: RiskMonitor,
        interval_sec: int = 60,
    ) -> None

    def run_once(self) -> None
    # テスト用: 各 Monitor の check_once() を1回呼び出す

    def run(self) -> None
    # 本番用: KeyboardInterrupt まで interval_sec 間隔でポーリング
```

### ポーリング動作

```python
def run(self) -> None:
    while True:
        try:
            self.run_once()
        except Exception:
            logger.exception("MonitoringEngine run_once failed")
        time.sleep(self.interval_sec)
```

`run_once()` 内の例外は握りつぶさずログに残し、次のポーリングサイクルを継続する。

---

## 7. StreamlitDashboard (`streamlit_dashboard.py`)

Monitoring.md § 10 の仕様に準拠。

### 画面構成（4タブ）

| タブ | 表示内容 | データソース |
|---|---|---|
| Overview | portfolio_value / cash / drawdown_pct | `dashboard` テーブル |
| Positions | 保有ポジション一覧（code / qty / avg_price / current_price） | `positions` テーブル |
| Orders | trade_logs 最新20件（logged_at / event_type / code / side / qty / state） | `trade_logs` テーブル |
| System | system_status 最新状態 + risk_logs 最新10件 | `system_status` / `risk_logs` テーブル |

### 自動リフレッシュ

```python
st.rerun(every=30)  # 30秒ごとに自動更新
```

### 起動方法

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

DB パスはコマンドライン引数で受け取る（デフォルト: `data/monitoring.db`）。

---

## 8. テスト方針

各クラスを `tests/test_monitoring_engine.py` と `tests/test_streamlit_dashboard.py` でカバーする。

| テスト対象 | 内容 |
|---|---|
| `SystemMonitor.check_once()` | PID なし / PID あり + プロセス生存 / stale PID の3ケース、データ鮮度 OK/NG |
| `TradeMonitor.check_once()` | 滞留なし / 滞留あり / 約定異常あり |
| `RiskMonitor.check_once()` | DD 閾値以下 / 超過、ポジション数正常 / 超過 |
| `MonitoringEngine.run_once()` | 3 Monitor が呼ばれることを確認（mock） |
| `StreamlitDashboard` | `get_dashboard()` の None / データあり、positions/orders 表示ロジック |

`psutil` / `duckdb` の呼び出しはテスト内で mock する。Streamlit のテストは `unittest.mock.patch("streamlit.*")` で UI 呼び出しをモックする。

---

## 9. 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `src/kabusys/monitoring/system_monitor.py` | 新規 |
| `src/kabusys/monitoring/trade_monitor.py` | 新規 |
| `src/kabusys/monitoring/risk_monitor.py` | 新規 |
| `src/kabusys/monitoring/monitoring_engine.py` | 新規 |
| `src/kabusys/monitoring/streamlit_dashboard.py` | 新規 |
| `src/kabusys/monitoring/__init__.py` | 更新（新クラスをエクスポート） |
| `tests/test_monitoring_engine.py` | 新規 |
| `tests/test_streamlit_dashboard.py` | 新規 |

---

## 10. 依存ライブラリ

| ライブラリ | 用途 | 追加要否 |
|---|---|---|
| `psutil` | CPU/メモリ/ディスク取得 | 要確認（未追加の可能性） |
| `streamlit` | ダッシュボード UI | 要確認（未追加の可能性） |
| `duckdb` | データ鮮度チェック | 既存 |
