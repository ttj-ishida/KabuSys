# バックテスト結果 DB 永続化 設計仕様

## Goal

`run_backtest()` の実行結果（メタデータ・集計指標・個別約定・日次エクイティカーブ）を DuckDB に永続化し、Streamlit UI（Issue #260）および AI 対話ウィザード（Issue #233）が信頼できるインデックスとして参照できるようにする。

## Architecture

既存の `report.py`（ファイル保存）は変更せず、新規の `persistence.py` に DB 保存ロジックを分離する。`run.py`（CLI）が `save_report()` 完了後に `save_backtest_to_db()` を呼び出す。バックテスト実行用インメモリDB（look-ahead-bias 防止）と永続化先の本番 DuckDB は別接続で完全分離する。

## Tech Stack

Python 3.10+, DuckDB, 既存 `src/kabusys/data/schema.py`（`_ALL_DDL` / `_MIGRATIONS`）, `src/kabusys/backtest/report.py`（`BacktestReport`）, `src/kabusys/backtest/engine.py`（`BacktestResult`）

---

## テーブル定義

3テーブルを `src/kabusys/data/schema.py` の `_ALL_DDL` に追加し、マイグレーションエントリを `_MIGRATIONS` に登録する。

### `backtest_runs`

実行メタデータと集計指標を保持する。指標はフラットカラム（`WHERE sharpe > 1.0` 等での絞り込み用）。`params_json` は再現性確保用の全パラメータ JSON。

```sql
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id                  VARCHAR       PRIMARY KEY,
    created_at              TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    start_date              DATE          NOT NULL,
    end_date                DATE          NOT NULL,
    initial_cash            DECIMAL(18,2) NOT NULL,
    scope_mode              VARCHAR       NOT NULL,
    scope_codes_json        VARCHAR,
    params_json             VARCHAR       NOT NULL,
    cagr                    DOUBLE,
    sharpe                  DOUBLE,
    max_drawdown            DOUBLE,
    win_rate                DOUBLE,
    payoff_ratio            DOUBLE,
    profit_factor           DOUBLE,
    annual_volatility       DOUBLE,
    calmar_ratio            DOUBLE,
    avg_holding_days        DOUBLE,
    total_trades            INTEGER,
    effective_universe_size INTEGER
)
```

- `run_id`: `BacktestReport.meta.run_id`（タイムスタンプベースUUID、CLI実行ごとに一意）
- `scope_mode`: `'default_universe'` または `'manual_codes'`
- `scope_codes_json`: `manual_codes` 時のみ JSON 配列文字列、それ以外は NULL
- `params_json`: `run_backtest()` に渡した全パラメータを JSON シリアライズ

### `backtest_trades`

個別約定明細。`TradeRecord` を 1 行 1 トレードで格納。

```sql
CREATE TABLE IF NOT EXISTS backtest_trades (
    run_id        VARCHAR       NOT NULL,
    date          DATE          NOT NULL,
    code          VARCHAR       NOT NULL,
    side          VARCHAR       NOT NULL,
    shares        INTEGER       NOT NULL,
    price         DECIMAL(18,4) NOT NULL,
    commission    DECIMAL(18,4) NOT NULL,
    realized_pnl  DECIMAL(18,4),
    PRIMARY KEY (run_id, date, code, side)
)
```

### `backtest_daily_equity`

日次エクイティカーブ。Streamlit でのグラフ表示用。

```sql
CREATE TABLE IF NOT EXISTS backtest_daily_equity (
    run_id           VARCHAR       NOT NULL,
    date             DATE          NOT NULL,
    portfolio_value  DECIMAL(18,2) NOT NULL,
    cash             DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (run_id, date)
)
```

---

## モジュール設計

### 新規: `src/kabusys/backtest/persistence.py`

```python
def save_backtest_to_db(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    result: BacktestResult,
    report: BacktestReport,
) -> None:
```

- `backtest_runs` に 1 行 INSERT
- `backtest_trades` に `result.trades` を `executemany` で一括 INSERT
- `backtest_daily_equity` に `result.history` を `executemany` で一括 INSERT
- 3テーブルへの書き込みを単一トランザクションで実行（失敗時 ROLLBACK）
- `run_id` の一意性は呼び出し元が保証する（既存 run_id への重複 INSERT は PRIMARY KEY 制約エラー）

### 変更: `src/kabusys/backtest/run.py`

`save_report()` の直後に DB 永続化を追加する。

```python
# 既存（変更なし）
save_report(report, result, output_dir=args.output_dir)

# 追加: 本番 DuckDB への永続化
conn_persist = duckdb.connect(str(db_path))
try:
    save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
    logger.info("バックテスト結果を DB に保存しました: run_id=%s", report.meta.run_id)
except Exception:
    logger.warning("DB 保存に失敗しました（ファイル保存は完了済み）", exc_info=True)
finally:
    conn_persist.close()
```

- バックテスト実行用のインメモリ `conn`（look-ahead-bias 防止用）とは**別接続**
- DB 保存失敗は警告ログのみ（ファイル保存は完了済みのため致命的ではない）
- `db_path` は既存の `--db` CLI オプションで渡された本番 DuckDB パス

### 変更: `src/kabusys/data/schema.py`

`_ALL_DDL` に 3 テーブルの DDL を追加する。`_MIGRATIONS` にマイグレーションエントリを追加し、既存 DB への後付け追加を冪等に処理する。

---

## データフロー

```
python -m kabusys.backtest.run --start 2024-01-01 --end 2024-12-31 --db kabusys.duckdb
    │
    ├─ run_backtest(in-memory conn)  →  BacktestResult
    ├─ build_report(result)          →  BacktestReport
    ├─ save_report(report, result)   →  artifacts/backtests/{run_id}/ (JSON/CSV/MD)
    │
    └─ save_backtest_to_db(persist_conn, run_id, result, report)
           ├─ INSERT INTO backtest_runs       (1 row)
           ├─ INSERT INTO backtest_trades     (N rows)
           └─ INSERT INTO backtest_daily_equity (M rows)
```

---

## エラーハンドリング

| ケース | 挙動 |
|---|---|
| DB ファイルが存在しない | `duckdb.connect()` が自動作成、スキーマ未初期化のため PK 制約エラー → `logger.warning` で続行 |
| 同一 run_id の重複実行 | PRIMARY KEY 制約エラー → `logger.warning` で続行（ファイルは保存済み） |
| DB 保存途中の例外 | ROLLBACK → `logger.warning` で続行 |
| インメモリ DB のスキーマ未初期化 | 影響なし（persist_conn は別接続） |

---

## テスト方針

`tests/test_backtest_persistence.py` を新規作成する。

- インメモリ DuckDB に 3 テーブルを DDL で作成
- `BacktestResult` と `BacktestReport` を最小限の dataclass で直接構築
- `save_backtest_to_db()` を呼び出し、3テーブルの行数・値を検証
- 重複 run_id での例外送出を検証
- trades / daily_equity が空の場合（0件）でも正常終了することを検証

---

## ファイル構成

| 操作 | パス | 役割 |
|---|---|---|
| Create | `src/kabusys/backtest/persistence.py` | DB 永続化ロジック |
| Create | `tests/test_backtest_persistence.py` | persistence.py のユニットテスト |
| Modify | `src/kabusys/data/schema.py` | 3テーブルの DDL・マイグレーション追加 |
| Modify | `src/kabusys/backtest/run.py` | CLI に `save_backtest_to_db()` 呼び出しを追加 |

---

## 対象外（スコープ外）

- バックテスト結果の削除・アーカイブ機能
- 既存ファイルアーティファクトからの DB インポート（過去実行分の遡及登録）
- `backtest_runs` 一覧表示 CLI コマンド（Streamlit #260 のスコープ）
- `backtest_daily_equity` のダウンサンプリング（行数削減）
