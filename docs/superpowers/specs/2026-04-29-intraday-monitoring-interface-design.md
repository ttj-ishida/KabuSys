# Intraday Monitoring Interface 設計仕様

- Issue: #203
- Date: 2026-04-29
- Status: 承認済み

---

## 1. 目的

ザラ場中（09:00〜15:00）にユーザーが異常を素早く検知し、対応判断できる監視インターフェースを提供する。

- **CLI `--watch` モード**: ターミナルで N 秒ごとに全ステータスを自動更新表示する
- **Streamlit ダッシュボード強化**: 既存ダッシュボードに Kill Switch・PID 状態・自動更新を追加する

---

## 2. アーキテクチャ

### 2.1 ファイル構成

```
src/kabusys/operations/
└── intraday_collector.py        # 新規: monitoring DB 読み取り専用（純粋関数）

src/kabusys/
└── run_intraday_monitor.py      # 新規: CLI エントリーポイント（--watch）

src/kabusys/monitoring/
├── streamlit_dashboard.py       # 既存強化: Kill Switch・PID・自動更新を追加
└── run_monitoring.py            # 既存強化: monitoring.pid 書き込みを追加

tests/
└── test_intraday_collector.py   # 新規: intraday_collector のユニットテスト
```

### 2.2 データフロー

```
monitoring SQLite DB（monitoring_engine が書き込み済み）
  └─ intraday_collector.collect_intraday_snapshot(conn, settings)
       └─ IntradaySnapshot (dataclass)
            ├─ run_intraday_monitor.py  → CLI 表示（--watch）
            └─ streamlit_dashboard.py  → ブラウザ表示（自動更新）
```

### 2.3 DB 接続

```python
sqlite_uri = Path(settings.sqlite_path).resolve().as_uri() + "?mode=ro"
conn = sqlite3.connect(sqlite_uri, uri=True)
conn.row_factory = sqlite3.Row
```

---

## 3. データ収集（intraday_collector.py）

### 3.1 IntradaySnapshot dataclass

```python
@dataclass
class IntradaySnapshot:
    collected_at: str            # ISO8601 UTC
    # プロセス状態
    execution_pid_ok: bool       # execution.pid が存在し psutil で生存確認済み
    monitoring_pid_ok: bool      # monitoring.pid が存在し psutil で生存確認済み
    kill_switch_active: bool     # data/kill.flag の存在
    kill_switch_reason: str      # kill.flag の内容（発動していなければ空文字）
    # リスク
    drawdown_pct: float | None   # dashboard.drawdown_pct（DB 未更新なら None）
    stale_order_count: int       # risk_logs の STALE_ORDER 件数（直近1時間）
    order_error_count: int       # risk_logs の ORDER_ERROR 件数（直近1時間）
    # システム
    process_ok: bool             # system_status.process_ok（最新1件、DB 空なら True）
    cpu_percent: float | None    # system_status.cpu_percent（最新1件）
    memory_percent: float | None # system_status.memory_percent（最新1件）
    # 直近リスクイベント
    recent_risk_events: list[dict]  # risk_logs 直近10件
```

### 3.2 公開関数

```python
def check_pid_file(pid_path: Path) -> bool:
    """PID ファイルが存在し、記録された PID が psutil で生存していれば True。"""

def check_kill_switch(flag_path: Path) -> tuple[bool, str]:
    """(active, reason) を返す。flag がなければ (False, "")。"""

def get_dashboard_row(conn: sqlite3.Connection) -> dict | None:
    """dashboard テーブルの最新行を dict で返す。レコードなしなら None。"""

def count_recent_risk_events(
    conn: sqlite3.Connection, event_type: str, minutes: int = 60
) -> int:
    """指定 event_type の直近 N 分以内の件数を返す。"""

def get_latest_system_status(conn: sqlite3.Connection) -> dict | None:
    """system_status の最新1件を dict で返す。レコードなしなら None。"""

def get_recent_risk_events(
    conn: sqlite3.Connection, limit: int = 10
) -> list[dict]:
    """risk_logs を logged_at DESC で最新 limit 件返す。"""

def collect_intraday_snapshot(
    conn: sqlite3.Connection, settings: Settings
) -> IntradaySnapshot:
    """全チェック関数を呼び出して IntradaySnapshot を返す。"""
```

### 3.3 データソース一覧

| フィールド | ソース |
|---|---|
| `execution_pid_ok` | `settings.pid_file_path`（`data/execution.pid`）+ psutil |
| `monitoring_pid_ok` | `data/monitoring.pid`（固定パス）+ psutil |
| `kill_switch_active/reason` | `settings.kill_flag_path`（`data/kill.flag`）|
| `drawdown_pct` | `dashboard.drawdown_pct`（最新1件）|
| `stale_order_count` | `risk_logs WHERE event_type='STALE_ORDER' AND logged_at > now-60min` |
| `order_error_count` | `risk_logs WHERE event_type='ORDER_ERROR' AND logged_at > now-60min` |
| `process_ok` | `system_status.process_ok`（最新1件、DB 空なら True）|
| `cpu_percent` / `memory_percent` | `system_status`（最新1件、DB 空なら None）|
| `recent_risk_events` | `risk_logs ORDER BY logged_at DESC LIMIT 10` |

### 3.4 monitoring.pid パス

```python
_MONITORING_PID = Path("data/monitoring.pid")
```

`run_monitoring.py` にこの PID ファイルの書き込みを追加する（§5 参照）。

---

## 4. CLI エントリーポイント（run_intraday_monitor.py）

### 4.1 使用例

```
python -m kabusys.run_intraday_monitor
python -m kabusys.run_intraday_monitor --watch
python -m kabusys.run_intraday_monitor --watch --interval 60
```

### 4.2 オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--watch` | なし | N 秒ごとに画面を自動更新し続ける |
| `--interval SECONDS` | `30` | `--watch` 時の更新間隔（秒）|

### 4.3 ステータス判定

| 全体ステータス | 条件 |
|---|---|
| `CRITICAL` 🚫 | Kill Switch 発動 OR `execution_pid_ok == False` |
| `WARNING` ⚠️ | `drawdown_pct <= -0.10` OR `order_error_count > 0` OR `stale_order_count > 0` OR `monitoring_pid_ok == False` |
| `OK` ✅ | それ以外 |

### 4.4 出力例（OK 時）

```
====================================================
  KabuSys Intraday Monitor  2026-04-29 10:35:00 JST
  Status : ✅ OK
====================================================
  プロセス:
    [ok  ] execution.pid    稼働中 (PID: 12345)
    [ok  ] monitoring.pid   稼働中 (PID: 67890)
    [ok  ] Kill Switch      発動なし
----------------------------------------------------
  リスク:
    [ok  ] ドローダウン      -2.1%
    [ok  ] 注文エラー        0 件（直近1時間）
    [ok  ] 滞留注文          0 件（直近1時間）
----------------------------------------------------
  システム:
    [ok  ] API 接続          正常
    [ok  ] CPU               45.2%
    [ok  ] Memory            62.3%
====================================================
  次回更新: 30秒後  Ctrl+C で終了
====================================================
```

### 4.5 出力例（CRITICAL 時）

```
====================================================
  KabuSys Intraday Monitor  2026-04-29 10:48:22 JST
  Status : 🚫 CRITICAL
====================================================
  プロセス:
    [CRIT] execution.pid    停止（PID ファイルなし）
    [ok  ] monitoring.pid   稼働中 (PID: 67890)
    [CRIT] Kill Switch      発動中: Max drawdown exceeded
----------------------------------------------------
  リスク:
    [WARN] ドローダウン      -11.3%（閾値 -10% 超過）
    [WARN] 注文エラー        3 件（直近1時間）
    [ok  ] 滞留注文          0 件（直近1時間）
----------------------------------------------------
  システム:
    [ok  ] API 接続          正常
    [ok  ] CPU               52.1%
    [ok  ] Memory            68.4%
====================================================
  次回更新: 30秒後  Ctrl+C で終了
====================================================
```

### 4.6 --watch 動作フロー

```python
while True:
    snapshot = collect_intraday_snapshot(conn, settings)
    os.system("cls")          # Windows: 画面クリア
    print(format_cli_summary(snapshot, interval=args.interval))
    time.sleep(args.interval)
```

`--watch` なしの場合は1回表示して終了。

### 4.7 終了コード

| コード | 意味 |
|---|---|
| `0` | OK |
| `1` | WARNING または CRITICAL |

---

## 5. run_monitoring.py 強化（monitoring.pid 追記）

`run_monitoring.py` の main() に以下を追加する:

```python
_MONITORING_PID = _PROJECT_ROOT / "data" / "monitoring.pid"

# ループ開始前に PID ファイルを書き込む
_MONITORING_PID.parent.mkdir(parents=True, exist_ok=True)
_MONITORING_PID.write_text(str(os.getpid()))

# finally ブロックに削除を追加
_MONITORING_PID.unlink(missing_ok=True)
```

---

## 6. Streamlit ダッシュボード強化（streamlit_dashboard.py）

### 6.1 自動更新

```python
# sidebar
refresh_interval = st.sidebar.selectbox("自動更新間隔", [30, 60, 120], index=0)
st.sidebar.caption(f"{refresh_interval}秒ごとに自動更新")
# ページ末尾
time.sleep(refresh_interval)
st.rerun()
```

### 6.2 Overview タブ強化

Kill Switch ステータスを最上部に表示:

```python
kill_flag = Path(settings.kill_flag_path)
if kill_flag.exists():
    reason = kill_flag.read_text().strip()
    st.error(f"🚫 Kill Switch 発動中: {reason}")
else:
    st.success("✅ Kill Switch: 発動なし")
```

drawdown に WARNING 色付き:

```python
dd = dashboard["drawdown_pct"] * 100
st.metric("Drawdown", f"{dd:.2f}%", delta_color="inverse")
if dd <= -10.0:
    st.warning(f"⚠️ ドローダウン {dd:.2f}% — 閾値 -10% 超過")
```

注文エラー・滞留注文件数をメトリクスに追加。

### 6.3 System タブ強化

PID 状態を `st.metric` で表示:

```python
exec_ok = check_pid_file(Path(settings.pid_file_path))
mon_ok = check_pid_file(Path("data/monitoring.pid"))
col1.metric("Execution", "OK" if exec_ok else "DOWN")
col2.metric("Monitoring", "OK" if mon_ok else "DOWN")
```

---

## 7. テスト方針

### 7.1 テスト対象

- `intraday_collector.py` の全公開関数: インメモリ SQLite + `tmp_path` でテスト
- `check_pid_file` / `check_kill_switch`: `tmp_path` フィクスチャで実ファイルを使ってテスト

### 7.2 主要テストケース（15〜20件）

| テスト | 内容 |
|---|---|
| `test_check_pid_file_false_when_missing` | PID ファイルなし → False |
| `test_check_pid_file_true_for_current_process` | 自プロセスの PID を書いた場合 → True |
| `test_check_pid_file_false_when_stale_pid` | 存在しない PID を書いた場合 → False |
| `test_check_kill_switch_inactive` | flag ファイルなし → (False, "") |
| `test_check_kill_switch_active` | flag ファイルあり → (True, "reason string") |
| `test_get_dashboard_row_none_when_empty` | dashboard テーブル空 → None |
| `test_get_dashboard_row_returns_drawdown` | dashboard あり → drawdown_pct が正しい |
| `test_count_recent_risk_events_zero_when_empty` | risk_logs 空 → 0 |
| `test_count_recent_risk_events_within_window` | 60分以内のレコードのみカウント |
| `test_count_recent_risk_events_ignores_old` | 60分超のレコードは無視 |
| `test_count_recent_risk_events_ignores_other_type` | 異なる event_type は無視 |
| `test_get_latest_system_status_none_when_empty` | system_status 空 → None |
| `test_get_latest_system_status_returns_latest` | 複数行 → logged_at が最新の1件 |
| `test_get_recent_risk_events_empty` | risk_logs 空 → [] |
| `test_get_recent_risk_events_limit` | limit=3 なら3件以内 |
| `test_collect_intraday_snapshot_all_ok` | 全フィールドを正常値で統合テスト |
| `test_collect_intraday_snapshot_kill_switch_active` | kill.flag あり → kill_switch_active=True |
| `test_collect_intraday_snapshot_no_db_data` | DB 空 → drawdown_pct=None, process_ok=True |
