# Market Close Summary 設計仕様

- Issue: #205
- Date: 2026-04-29
- Status: 承認済み

---

## 1. 目的

市場終了後（15:30 頃）に「今日の運用が正常に締まったか」を 1 コマンドで確認し、
夜間バッチへ進んでよいかを判断できる締めレポートを提供する。

---

## 2. アーキテクチャ

### 2.1 ファイル構成

```
src/kabusys/operations/
├── market_close_collector.py   # DB クエリ専用（DuckDB + SQLite）
├── market_close_report.py      # 純粋関数（build / format / save）
src/kabusys/
├── run_market_close_report.py  # CLI エントリーポイント
tests/
├── test_market_close_report.py # ユニットテスト
```

### 2.2 データフロー

```
run_market_close_report.py
  └─ market_close_collector.collect_market_close_data(duckdb_conn, sqlite_conn, today)
       └─ MarketCloseData (dataclass)
  └─ market_close_report.build_report(data, report_date)
       └─ MarketCloseReport (dataclass)
  └─ format_cli_summary / format_json / format_markdown / save_report
```

### 2.3 DB 接続

- DuckDB（read-only）: `positions`, `portfolio_performance`
- SQLite（read-only、`mode=ro` URI）: `signal_queue`

---

## 3. データ収集（market_close_collector.py）

### 3.1 MarketCloseData dataclass

```python
@dataclass
class MarketCloseData:
    signal_pending_count: int        # 当日 pending シグナル件数
    positions_updated: bool          # positions に当日分が存在するか
    performance_recorded: bool       # portfolio_performance に当日分が存在するか
    filled_count: int                # 当日 filled シグナル件数
    daily_return: float | None       # 当日日次リターン（未記録なら None）
    equity_today: float | None       # 当日期末資産（未記録なら None）
    equity_prev: float | None        # 前営業日期末資産（存在しなければ None）
```

### 3.2 クエリ一覧

| フィールド | 情報源 | クエリ概要 |
|---|---|---|
| `signal_pending_count` | SQLite: `signal_queue` | `WHERE date=today AND status='pending'` の COUNT |
| `positions_updated` | DuckDB: `positions` | `MAX(date) = today` なら True |
| `performance_recorded` | DuckDB: `portfolio_performance` | `WHERE date=today` のレコード存在確認 |
| `filled_count` | SQLite: `signal_queue` | `WHERE date=today AND status='filled'` の COUNT |
| `daily_return` | DuckDB: `portfolio_performance` | `WHERE date=today` の `daily_return`（未記録なら None）|
| `equity_today` | DuckDB: `portfolio_performance` | `WHERE date=today` の `equity`（未記録なら None）|
| `equity_prev` | DuckDB: `portfolio_performance` | `WHERE date < today ORDER BY date DESC LIMIT 1` の `equity` |

### 3.3 公開関数

pre_market_collector と同様に、各チェック関数を個別に公開して直接テスト可能にする。

```python
def check_signal_pending(sqlite_conn, today: date) -> int: ...
def check_signal_filled(sqlite_conn, today: date) -> int: ...
def check_positions_updated(duckdb_conn, today: date) -> bool: ...
def check_performance_recorded(duckdb_conn, today: date) -> bool: ...
def get_performance_row(duckdb_conn, today: date) -> tuple[float | None, float | None]: ...
    # -> (daily_return, equity_today)
def get_prev_equity(duckdb_conn, today: date) -> float | None: ...

def collect_market_close_data(
    duckdb_conn,
    sqlite_conn,
    today: date,
) -> MarketCloseData:
    """上記の各関数を呼び出して MarketCloseData を返す。"""
    ...
```

---

## 4. レポート生成（market_close_report.py）

### 4.1 定数

```python
STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED"
```

### 4.2 データクラス

```python
@dataclass
class CheckItem:
    name: str
    status: str   # "ok" | "failed"
    detail: str

@dataclass
class MarketCloseReport:
    report_date: str        # ISO date（YYYY-MM-DD）
    generated_at: str       # ISO 8601 UTC
    status: str             # "OK" / "BLOCKED"
    checks: list[CheckItem] # 3 項目
    summary: dict           # 約定件数・日次リターン・損益額・期末資産
    warnings: list[str]     # BLOCKED 理由の文字列リスト
```

### 4.3 ステータス判定

BLOCKED 条件（いずれかが真）:
- `signal_pending_count > 0`（pending シグナル残件あり）
- `positions_updated == False`（positions 未更新）
- `performance_recorded == False`（portfolio_performance 未記録）

それ以外: `OK`

### 4.4 チェック項目（3件）

| name | ok 条件 | detail 例（ok） | detail 例（failed） |
|---|---|---|---|
| `signal_queue` | `pending == 0` | `pending: 0 件（全シグナル処理済み）` | `pending: 2 件（未処理シグナルあり）` |
| `positions` | `positions_updated` | `positions: 当日分 更新済み` | `positions: 当日分 未更新` |
| `portfolio_performance` | `performance_recorded` | `portfolio_performance: 当日分 記録済み` | `portfolio_performance: 当日分 未記録` |

### 4.5 summary フィールド

```python
summary = {
    "filled_count": filled_count,           # int
    "daily_return": daily_return,           # float | None
    "pnl_amount": equity_today - equity_prev if (equity_today and equity_prev) else None,
    "equity_today": equity_today,           # float | None
}
```

### 4.6 公開関数

```python
def build_report(data: MarketCloseData, *, report_date: date) -> MarketCloseReport: ...
def format_cli_summary(report: MarketCloseReport) -> str: ...
def format_json(report: MarketCloseReport) -> str: ...
def format_markdown(report: MarketCloseReport) -> str: ...
def save_report(report: MarketCloseReport, output_dir: Path | str | None = None) -> Path: ...
```

`save_report` は `report_date` をバリデーション（regex + `date.fromisoformat()`）し、
`artifacts/market_close/{report_date}/` に以下を保存する:
- `summary.json`
- `report.md`
- `warnings.json`

---

## 5. CLI エントリーポイント（run_market_close_report.py）

### 5.1 使用例

```cmd
python -m kabusys.run_market_close_report
python -m kabusys.run_market_close_report --date 2026-04-28
python -m kabusys.run_market_close_report --save
python -m kabusys.run_market_close_report --json
python -m kabusys.run_market_close_report --save --json
```

### 5.2 オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--date YYYY-MM-DD` | 今日 | レポートの日付ラベル兼クエリ対象日（`signal_queue.date`・`positions.date`・`portfolio_performance.date` の絞り込みに使用） |
| `--save` | なし | `artifacts/market_close/` に保存 |
| `--json` | なし | JSON 形式で標準出力 |

### 5.3 終了コード

| コード | 意味 |
|---|---|
| `0` | OK（夜間バッチへ進んでよい） |
| `1` | BLOCKED（要確認） |

### 5.4 DB 接続

```python
duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
sqlite_uri = Path(settings.sqlite_path).resolve().as_uri() + "?mode=ro"
sqlite_conn = sqlite3.connect(sqlite_uri, uri=True)
```

---

## 6. 出力例

### CLI（OK 時）

```
====================================================
  Market Close Summary  2026-04-28
  Status : ✅ OK
====================================================
  Checks:
    [ok  ] signal_queue         pending: 0 件（全シグナル処理済み）
    [ok  ] positions            positions: 当日分 更新済み
    [ok  ] portfolio_performance portfolio_performance: 当日分 記録済み
----------------------------------------------------
  Summary:
    約定件数    : 5 件
    日次リターン : +0.32%
    当日損益額  : +¥16,400
    期末総資産  : ¥5,234,000
====================================================
```

### CLI（BLOCKED 時）

```
====================================================
  Market Close Summary  2026-04-28
  Status : 🚫 BLOCKED
====================================================
  Checks:
    [FAIL] signal_queue         pending: 2 件（未処理シグナルあり）
    [ok  ] positions            positions: 当日分 更新済み
    [ok  ] portfolio_performance portfolio_performance: 当日分 記録済み
----------------------------------------------------
  Warnings:
    [!] signal_queue に本日の pending シグナルが 2 件残っています
====================================================
```

---

## 7. テスト方針

### 7.1 テスト対象

- `market_close_report.py`（純粋関数）: `build_report`、`format_*`、`save_report`
- `market_close_collector.py`（DB クエリ）: インメモリ DuckDB + SQLite でテスト

### 7.2 主要テストケース（25〜30 件を想定）

| テスト | 内容 |
|---|---|
| `test_build_report_ok` | 全チェック OK → status = "OK" |
| `test_build_report_blocked_pending` | pending > 0 → BLOCKED |
| `test_build_report_blocked_positions` | positions 未更新 → BLOCKED |
| `test_build_report_blocked_performance` | portfolio_performance 未記録 → BLOCKED |
| `test_build_report_all_blocked` | 3 条件すべて → BLOCKED、warnings 3 件 |
| `test_pnl_amount_calculated` | equity_today - equity_prev が正しく計算される |
| `test_pnl_amount_none_when_missing` | equity_prev が None → pnl_amount = None |
| `test_format_cli_summary_ok` | CLI 出力に ✅ OK が含まれる |
| `test_format_cli_summary_blocked` | CLI 出力に 🚫 BLOCKED と warnings が含まれる |
| `test_format_cli_summary_summary_section` | 約定件数・日次リターン・損益額・期末資産が表示される |
| `test_format_json` | JSON が正しくシリアライズされる |
| `test_format_markdown` | Markdown に全セクションが含まれる |
| `test_save_report_creates_files` | 3 ファイルが正しいパスに生成される |
| `test_save_report_invalid_date_format` | 不正フォーマットで ValueError |
| `test_save_report_invalid_calendar_date` | 不正カレンダー日（2026-99-99）で ValueError |
| `test_collect_signal_pending_count` | pending 件数クエリが正しい |
| `test_collect_signal_filled_count` | filled 件数クエリが正しい |
| `test_collect_positions_updated_true` | 当日 positions あり → True |
| `test_collect_positions_updated_false` | 当日 positions なし → False |
| `test_collect_performance_recorded_true` | 当日 portfolio_performance あり → True |
| `test_collect_performance_recorded_false` | 当日 portfolio_performance なし → False |
| `test_collect_equity_prev_none_when_no_history` | 前日レコードなし → equity_prev = None |
| `test_collect_daily_return_none_when_not_recorded` | 当日レコードなし → daily_return = None |
