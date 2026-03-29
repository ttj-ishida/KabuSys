# SQLite監視ログDB 設計仕様

> **For agentic workers:** このドキュメントは Issue #36「SQLite監視ログDB実装」の設計仕様です。
> 実装前に必ず本ドキュメントを参照してください。

---

## 1. 目的

`src/kabusys/monitoring/monitoring_db.py` を実装し、Phase 7 監視システムの永続化基盤を構築する。
起動時システム状態・発注イベント・保有ポジション・リスクイベント・ダッシュボード集計を SQLite に記録し、
後続の監視エンジン（#37, #38）および Streamlit ダッシュボード（#35）から参照できるようにする。

対象 Issue: #36「【Phase 7】SQLite監視ログDB実装」

---

## 2. 前提・既存インフラ

| 要素 | 場所 | 内容 |
|------|------|------|
| `config.sqlite_path` | `src/kabusys/config.py:166` | DB ファイルパス（デフォルト `data/monitoring.db`、`SQLITE_PATH` 環境変数で上書き可） |
| `init_orders_db()` / `OrderRepository` | `order_repository.py` | 参考にする実装パターン（`init_*` 関数 + Repository クラス） |

接続管理は呼び出し側（監視エンジン等）が担当。`MonitoringDB` は `conn` を受け取るだけ。

---

## 3. アーキテクチャ

```
src/kabusys/monitoring/
├── __init__.py        ← MonitoringDB, init_monitoring_db をエクスポート追加
└── monitoring_db.py   ← 新規作成

tests/
└── test_monitoring_db.py  ← 新規作成
```

`monitoring_db.py` の構成は `order_repository.py` と対称:

```
init_monitoring_db(conn)  ← 5テーブル + インデックス作成（冪等）
MonitoringDB(conn)        ← DB 操作クラス（読み書きのみ、ビジネスロジックなし）
```

---

## 4. テーブルスキーマ

### 4.1 `system_status` — システム状態（追記）

```sql
CREATE TABLE IF NOT EXISTS system_status (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at    TEXT    NOT NULL,          -- ISO8601 UTC
    cpu_percent    REAL    NOT NULL,
    memory_percent REAL    NOT NULL,
    disk_percent   REAL    NOT NULL,
    process_ok     INTEGER NOT NULL           -- 1=正常, 0=異常
);
CREATE INDEX IF NOT EXISTS idx_system_status_recorded_at ON system_status (recorded_at);
```

用途: 60秒ごとのポーリングで追記。CPU > 90% / メモリ > 85% 等の監視エンジン（#37）が参照。

### 4.2 `trade_logs` — 発注イベントログ（追記）

```sql
CREATE TABLE IF NOT EXISTS trade_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at       TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,  -- 'order_created'|'order_sent'|'filled'|'cancelled'|'rejected'
    client_order_id TEXT    NOT NULL,
    code            TEXT    NOT NULL,
    side            TEXT    NOT NULL,  -- 'buy'|'sell'
    qty             INTEGER NOT NULL,
    price           REAL    NOT NULL,
    filled_qty      INTEGER NOT NULL DEFAULT 0,
    state           TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trade_logs_logged_at       ON trade_logs (logged_at);
CREATE INDEX IF NOT EXISTS idx_trade_logs_client_order_id ON trade_logs (client_order_id);
```

用途: 発注・約定・キャンセル等のイベントを時系列で記録。`orders` テーブルの変化をここに反映する（呼び出し元が明示的に書き込む）。

### 4.3 `positions` — 保有ポジション（upsert）

```sql
CREATE TABLE IF NOT EXISTS positions (
    code          TEXT  PRIMARY KEY,
    qty           INTEGER NOT NULL,
    avg_price     REAL    NOT NULL,
    current_price REAL,               -- NULL = 未取得
    updated_at    TEXT    NOT NULL
);
```

用途: code ごとに最新の保有状況を保持。約定通知受信時に upsert、ポジション解消時に削除。

### 4.4 `risk_logs` — リスクイベントログ（追記）

```sql
CREATE TABLE IF NOT EXISTS risk_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at    TEXT    NOT NULL,
    event_type   TEXT    NOT NULL,  -- 'drawdown_warning'|'position_limit'|'sector_concentration'|'circuit_breaker'
    metric_name  TEXT    NOT NULL,  -- 例: 'drawdown_pct'
    metric_value REAL    NOT NULL,
    threshold    REAL    NOT NULL,
    detail       TEXT               -- 追加情報（JSON 文字列等、NULL 可）
);
CREATE INDEX IF NOT EXISTS idx_risk_logs_logged_at   ON risk_logs (logged_at);
CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type  ON risk_logs (event_type);
```

用途: DD超過・ポジション上限・サーキットブレーカー発動等をログ。監視エンジン（#38）・Slack アラート（#39）が参照。

### 4.5 `dashboard` — ダッシュボード集計（1行 upsert）

```sql
CREATE TABLE IF NOT EXISTS dashboard (
    id                INTEGER PRIMARY KEY DEFAULT 1,
    updated_at        TEXT    NOT NULL,
    portfolio_value   REAL    NOT NULL,
    cash              REAL    NOT NULL,
    drawdown_pct      REAL    NOT NULL,
    open_order_count  INTEGER NOT NULL,
    position_count    INTEGER NOT NULL
);
```

用途: push 通知受信のたびに最新値を `INSERT OR REPLACE` で id=1 に上書き。Streamlit が常に最新状態を参照。

---

## 5. `MonitoringDB` クラス API

```python
class MonitoringDB:
    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        self._conn = conn

    # --- system_status ---
    def log_system_status(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        process_ok: bool,
        recorded_at: datetime | None = None,   # None → datetime.now(UTC)
    ) -> None: ...

    # --- trade_logs ---
    def log_trade_event(
        self,
        event_type: str,
        client_order_id: str,
        code: str,
        side: str,
        qty: int,
        price: float,
        state: str,
        filled_qty: int = 0,
        logged_at: datetime | None = None,
    ) -> None: ...

    # --- positions ---
    def upsert_position(
        self,
        code: str,
        qty: int,
        avg_price: float,
        current_price: float | None = None,
        updated_at: datetime | None = None,
    ) -> None: ...

    def delete_position(self, code: str) -> None: ...

    # --- risk_logs ---
    def log_risk_event(
        self,
        event_type: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        detail: str | None = None,
        logged_at: datetime | None = None,
    ) -> None: ...

    # --- dashboard ---
    def upsert_dashboard(
        self,
        portfolio_value: float,
        cash: float,
        drawdown_pct: float,
        open_order_count: int,
        position_count: int,
        updated_at: datetime | None = None,
    ) -> None: ...

    def get_dashboard(self) -> dict | None: ...   # Streamlit 向け読み取り
```

**設計方針:**
- 全書き込みメソッドの `*_at` 引数はデフォルト `None` → 内部で `datetime.now(timezone.utc)` を使用（テスト時は明示注入）
- `upsert_dashboard`: `INSERT OR REPLACE INTO dashboard` で id=1 固定
- `upsert_position`: `INSERT OR REPLACE INTO positions` で code をキー
- エラーハンドリングは呼び出し側に委ねる（リポジトリ層は素直な読み書きのみ）

---

## 6. エクスポート

### `src/kabusys/monitoring/__init__.py`

```python
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

__all__ = ["MonitoringDB", "init_monitoring_db"]
```

---

## 7. テスト仕様（`tests/test_monitoring_db.py`）

`conftest.py` に `monitoring_conn` フィクスチャを追加:

```python
@pytest.fixture
def monitoring_conn():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    yield conn
    conn.close()
```

| テストクラス / ケース | 検証内容 |
|---|---|
| `TestInitMonitoringDb` | |
| `test_tables_created_idempotently` | `init_monitoring_db` を2回呼んでもエラーなし |
| `TestLogSystemStatus` | |
| `test_appends_row` | 行が追記される |
| `test_default_recorded_at_is_utc_now` | `recorded_at` 引数省略時に UTC タイムスタンプが入る |
| `TestLogTradeEvent` | |
| `test_appends_row_with_correct_fields` | 全フィールドが正しく保存される |
| `TestUpsertPosition` | |
| `test_insert_new_position` | 新規 code が挿入される |
| `test_update_existing_position` | 同一 code を2回 upsert すると上書きされる（行数は1のまま） |
| `test_delete_position` | `delete_position` 後にその code は取得されない |
| `TestLogRiskEvent` | |
| `test_appends_row` | 全フィールドが正しく保存される |
| `TestUpsertDashboard` | |
| `test_first_upsert_creates_row` | 最初の upsert でレコードが作成される |
| `test_second_upsert_overwrites` | 2回 upsert しても行数は1のまま、値は最新 |
| `test_get_dashboard_returns_latest` | `get_dashboard()` が最新の dict を返す |
| `test_get_dashboard_returns_none_when_empty` | レコードなし時は `None` を返す |

---

## 8. ファイル変更サマリー

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/kabusys/monitoring/monitoring_db.py` | 新規作成 | `init_monitoring_db`, `MonitoringDB` |
| `src/kabusys/monitoring/__init__.py` | 修正 | `MonitoringDB`, `init_monitoring_db` をエクスポート |
| `tests/conftest.py` | 修正 | `monitoring_conn` フィクスチャ追加 |
| `tests/test_monitoring_db.py` | 新規作成 | 上記テストケース |
