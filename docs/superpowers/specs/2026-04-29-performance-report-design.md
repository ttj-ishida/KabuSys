# 運用成績サマリーレポート 設計仕様

- Issue: #195
- Date: 2026-04-29
- Status: 承認済み

---

## 1. 目的

日次・週次・月次の運用成績サマリーレポートを 1 コマンドで生成し、
`live` および `paper_trading` 環境それぞれの成績を Markdown で出力する。

---

## 2. アーキテクチャ

### 2.1 ファイル構成

```
src/kabusys/operations/
├── performance_collector.py    # DuckDB クエリ専用（純粋関数）
└── performance_report.py       # build / format / save（純粋関数）

src/kabusys/
└── run_performance_report.py   # CLI エントリーポイント

tests/
└── test_performance_report.py  # ユニットテスト
```

### 2.2 データフロー

```
DuckDB: portfolio_performance (env 列追加済み)
DuckDB: market_calendar          ← JPX 営業週の境界決定
  └─ performance_collector.collect_daily_rows(conn, env, from_date, to_date)
       → list[DailyRow]
  └─ performance_collector.collect_weekly_rows(conn, env, from_date, to_date)
       → list[WeeklyRow]
  └─ performance_collector.collect_monthly_rows(conn, env, from_date, to_date)
       → list[MonthlyRow]
           └─ performance_report.build_report(rows, report_type, env, from_date, to_date)
                → PerformanceReport (dataclass)
                    └─ format_markdown / save_report
```

### 2.3 DB 接続

```python
duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
```

---

## 3. スキーマ変更

### 3.1 portfolio_performance への env 列追加

```sql
ALTER TABLE portfolio_performance
ADD COLUMN env VARCHAR DEFAULT 'live';
```

既存レコードは `DEFAULT 'live'` でバックフィル。

### 3.2 Execution 書き込み側の変更

`portfolio_performance` へのレコード挿入時に `settings.env` を `env` 列に書き込む。

---

## 4. データ収集（performance_collector.py）

### 4.1 データクラス定義

```python
@dataclass
class DailyRow:
    date: date
    env: str
    equity: float
    daily_return: float | None     # portfolio_performance.daily_return
    drawdown: float | None         # portfolio_performance.drawdown
    cumulative_return: float | None  # (equity / first_equity_in_period) - 1.0

@dataclass
class WeeklyRow:
    week_label: str           # "2026-W17"（ISO 週番号）
    trading_days: int         # JPX 営業日数（market_calendar 参照）
    equity_start: float | None
    equity_end: float | None
    weekly_return: float | None    # (equity_end / equity_start) - 1.0
    max_drawdown: float | None     # 週内の drawdown 最小値
    win_days: int             # daily_return > 0 の日数

@dataclass
class MonthlyRow:
    month_label: str          # "2026-04"
    trading_days: int
    equity_start: float | None
    equity_end: float | None
    monthly_return: float | None   # (equity_end / equity_start) - 1.0
    max_drawdown: float | None     # 月内の drawdown 最小値
    win_days: int
```

### 4.2 公開関数

```python
def collect_daily_rows(
    conn,               # DuckDB connection
    env: str,           # "live" | "paper_trading"
    from_date: date,
    to_date: date,
) -> list[DailyRow]:
    """portfolio_performance から日次行を取得。
    cumulative_return は期間内最初の equity を基準に計算。
    env でフィルタするため live と paper_trading データが混在しない。
    """

def collect_weekly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[WeeklyRow]:
    """collect_daily_rows の結果を ISO 週番号でグループ化して集約。
    JPX 営業日数は market_calendar WHERE open_market=1 で取得。
    """

def collect_monthly_rows(
    conn,
    env: str,
    from_date: date,
    to_date: date,
) -> list[MonthlyRow]:
    """collect_daily_rows の結果を (year, month) でグループ化して集約。"""
```

### 4.3 クエリ詳細

**collect_daily_rows:**

```sql
SELECT date, env, equity, daily_return, drawdown
FROM portfolio_performance
WHERE env = ?
  AND date >= ?
  AND date <= ?
ORDER BY date ASC
```

`cumulative_return` は Python 側で計算: `(equity / first_equity) - 1.0`

**JPX 営業日数（WeeklyRow / MonthlyRow 用）:**

```sql
SELECT COUNT(*) FROM market_calendar
WHERE market_date >= ?
  AND market_date <= ?
  AND open_market = 1
```

---

## 5. レポート生成（performance_report.py）

### 5.1 データクラス

```python
@dataclass
class PerformanceReport:
    report_type: str         # "daily" | "weekly" | "monthly"
    env: str                 # "live" | "paper_trading"
    generated_at: str        # ISO 8601 UTC
    from_date: str           # YYYY-MM-DD
    to_date: str             # YYYY-MM-DD
    rows: list               # list[DailyRow | WeeklyRow | MonthlyRow]
    summary: dict
```

### 5.2 summary フィールド

```python
summary = {
    "total_trading_days": int,
    "cumulative_return": float | None,   # (最終 equity / 最初 equity) - 1.0
    "max_drawdown": float | None,        # 期間内 drawdown 最小値
    "win_rate": float | None,            # win_days / total_trading_days
    "equity_start": float | None,
    "equity_end": float | None,
}
```

`rows` が空の場合、`summary` の各値は `None`（`total_trading_days` は `0`）。

### 5.3 公開関数

```python
def build_report(
    rows: list,
    *,
    report_type: str,
    env: str,
    from_date: date,
    to_date: date,
) -> PerformanceReport: ...

def format_markdown(report: PerformanceReport) -> str: ...

def save_report(
    report: PerformanceReport,
    output_dir: Path | str | None = None,
) -> Path:
    """artifacts/performance/{env}/{report_type}/{period}/report.md に保存。
    period は report の from_date〜to_date ではなく rows の末尾ラベルを使う:
      daily   → to_date (YYYY-MM-DD)
      weekly  → rows[-1].week_label (YYYY-Www)
      monthly → rows[-1].month_label (YYYY-MM)
    rows が空の場合は to_date を period ラベルとして使用。
    """
```

### 5.4 保存パス例

| type | 保存先 |
|---|---|
| daily | `artifacts/performance/live/daily/2026-04-28/report.md` |
| weekly | `artifacts/performance/live/weekly/2026-W17/report.md` |
| monthly | `artifacts/performance/live/monthly/2026-04/report.md` |

### 5.5 Markdown 出力例（daily）

```markdown
# 運用成績レポート（日次）

- 環境: live
- 期間: 2026-04-01 〜 2026-04-28
- 生成日時: 2026-04-29T09:00:00Z

## サマリー

| 項目 | 値 |
|---|---|
| 営業日数 | 20 日 |
| 累積リターン | +3.21% |
| 最大ドローダウン | -2.10% |
| 勝率 | 65.0% |
| 期首総資産 | ¥5,000,000 |
| 期末総資産 | ¥5,160,500 |

## 日次明細

| 日付 | 総資産 | 日次リターン | ドローダウン | 累積リターン |
|---|---|---|---|---|
| 2026-04-01 | ¥5,020,000 | +0.40% | -0.00% | +0.40% |
| 2026-04-02 | ¥5,010,000 | -0.20% | -0.20% | +0.20% |
```

### 5.6 Markdown 出力例（weekly）

```markdown
# 運用成績レポート（週次）

- 環境: live
- 期間: 2026-04-01 〜 2026-04-28

## サマリー
...（同上）

## 週次明細

| 週 | 営業日数 | 期首資産 | 期末資産 | 週次リターン | 最大DD | 勝ち日数 |
|---|---|---|---|---|---|---|
| 2026-W14 | 5 | ¥5,000,000 | ¥5,025,000 | +0.50% | -0.30% | 3 |
| 2026-W15 | 5 | ¥5,025,000 | ¥5,060,000 | +0.70% | -0.10% | 4 |
```

---

## 6. CLI エントリーポイント（run_performance_report.py）

### 6.1 使用例

```cmd
python -m kabusys.run_performance_report --type daily
python -m kabusys.run_performance_report --type weekly --env paper_trading
python -m kabusys.run_performance_report --type monthly --from 2026-01-01 --to 2026-04-30
python -m kabusys.run_performance_report --type daily --save
python -m kabusys.run_performance_report --type weekly --save --env live
```

### 6.2 オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--type daily\|weekly\|monthly` | 必須 | レポート種別 |
| `--env live\|paper_trading` | `live` | 対象環境 |
| `--from YYYY-MM-DD` | 過去30日 | 集計開始日 |
| `--to YYYY-MM-DD` | 今日 | 集計終了日 |
| `--save` | なし | `artifacts/performance/` に保存 |

### 6.3 終了コード

| コード | 意味 |
|---|---|
| `0` | 正常完了 |
| `1` | データなし（portfolio_performance に対象レコードなし） |
| `2` | 引数エラー |

---

## 7. テスト方針

### 7.1 テスト対象

- `performance_collector.py`: インメモリ DuckDB でテスト
- `performance_report.py`（純粋関数）: ダミーデータでテスト

### 7.2 主要テストケース

| テスト | 内容 |
|---|---|
| `test_collect_daily_rows_basic` | 基本的な日次行取得 |
| `test_collect_daily_rows_env_isolation` | live と paper_trading が混在しても正しく絞り込まれる |
| `test_collect_daily_rows_empty` | データなし → [] |
| `test_collect_daily_rows_cumulative_return` | 累積リターンが正しく計算される |
| `test_collect_daily_rows_date_filter` | from_date / to_date で正しく絞り込まれる |
| `test_collect_weekly_rows_grouping` | 同週の日次行が正しく集約される |
| `test_collect_weekly_rows_trading_days` | market_calendar の営業日数が正しい |
| `test_collect_weekly_rows_empty` | データなし → [] |
| `test_collect_monthly_rows_grouping` | 同月の日次行が正しく集約される |
| `test_collect_monthly_rows_trading_days` | market_calendar の営業日数が正しい |
| `test_build_report_summary_basic` | cumulative_return / max_drawdown / win_rate が正しい |
| `test_build_report_empty_rows` | rows=[] → summary 値が None（total_trading_days=0） |
| `test_build_report_win_rate` | daily_return > 0 の日数が正しくカウントされる |
| `test_format_markdown_daily` | サマリー表と日次明細テーブルが含まれる |
| `test_format_markdown_weekly` | 週次明細テーブルが含まれる |
| `test_format_markdown_monthly` | 月次明細テーブルが含まれる |
| `test_format_markdown_empty_rows` | データなし時も正常に出力される |
| `test_save_report_daily` | `artifacts/performance/live/daily/{date}/report.md` が生成される |
| `test_save_report_weekly` | `artifacts/performance/live/weekly/YYYY-Www/report.md` が生成される |
| `test_save_report_monthly` | `artifacts/performance/live/monthly/YYYY-MM/report.md` が生成される |
