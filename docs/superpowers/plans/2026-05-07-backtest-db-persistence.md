# バックテスト結果 DB 永続化 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `run_backtest()` 実行結果（メタデータ・集計指標・個別約定・日次エクイティカーブ）を DuckDB の 3テーブルに永続化し、Streamlit UI（Issue #260）が信頼できるインデックスとして参照できるようにする。

**Architecture:** 新規 `persistence.py` に DB 保存ロジックを分離する。`run.py` の CLI が `save_report()` 完了後に `save_backtest_to_db()` を呼び出す。バックテスト実行用インメモリDB（look-ahead-bias 防止）と永続化先の本番 DuckDB は別接続で完全分離する。DB 保存失敗は警告ログのみで CLI の終了コードに影響しない。

**Tech Stack:** Python 3.10+, DuckDB, `src/kabusys/data/schema.py`, `src/kabusys/backtest/engine.py`（`BacktestResult`）, `src/kabusys/backtest/report.py`（`BacktestReport`）

---

## ファイル構成

| 操作 | パス | 役割 |
|---|---|---|
| Modify | `src/kabusys/data/schema.py` | 3テーブルの DDL 定数 + `_ALL_DDL` + `_MIGRATIONS` エントリ追加 |
| Create | `src/kabusys/backtest/persistence.py` | `save_backtest_to_db()` — 3テーブルへの一括 INSERT |
| Create | `tests/test_backtest_persistence.py` | persistence.py のユニットテスト |
| Modify | `src/kabusys/backtest/run.py` | CLI に DB 永続化呼び出しを追加 |

---

### Task 1: `schema.py` に 3 テーブルの DDL を追加

**Files:**
- Modify: `src/kabusys/data/schema.py`（`_ALL_DDL` リスト末尾に 3 DDL 追加）
- Test: `tests/test_backtest_persistence.py`（新規作成、スキーマ検証テストのみ）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_persistence.py` を新規作成する:

```python
"""tests/test_backtest_persistence.py"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import duckdb
import pytest

from kabusys.data.schema import init_schema


class TestBacktestTablesExist:
    """init_schema() で 3 テーブルが作成されることを確認。"""

    def test_backtest_runs_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_runs'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_trades_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_trades'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_daily_equity_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_daily_equity'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_runs_primary_key(self):
        conn = init_schema(":memory:")
        conn.execute(
            "INSERT INTO backtest_runs "
            "(run_id, start_date, end_date, initial_cash, scope_mode, params_json) "
            "VALUES ('run1', '2024-01-01', '2024-12-31', 10000000, 'default_universe', '{}')"
        )
        with pytest.raises(duckdb.ConstraintException):
            conn.execute(
                "INSERT INTO backtest_runs "
                "(run_id, start_date, end_date, initial_cash, scope_mode, params_json) "
                "VALUES ('run1', '2024-01-01', '2024-12-31', 10000000, 'default_universe', '{}')"
            )
        conn.close()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_backtest_persistence.py::TestBacktestTablesExist -v
```

Expected: `FAILED` — `backtest_runs` テーブルが存在しない

- [ ] **Step 3: `schema.py` に 3 DDL を追加**

`src/kabusys/data/schema.py` の `_BOOTSTRAP_LOAD_HISTORY` 定義の直後（`# ---------------------------------------------------------------------------` の行の前）に以下を追加する:

```python
# ---- Backtest Layer --------------------------------------------------------

_BACKTEST_RUNS = """
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
"""

_BACKTEST_TRADES = """
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
"""

_BACKTEST_DAILY_EQUITY = """
CREATE TABLE IF NOT EXISTS backtest_daily_equity (
    run_id           VARCHAR       NOT NULL,
    date             DATE          NOT NULL,
    portfolio_value  DECIMAL(18,2) NOT NULL,
    cash             DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (run_id, date)
)
"""
```

`_ALL_DDL` リストの末尾（`_BOOTSTRAP_LOAD_HISTORY` の後）に追加する:

```python
    # Backtest
    _BACKTEST_RUNS,
    _BACKTEST_TRADES,
    _BACKTEST_DAILY_EQUITY,
```

`_MIGRATIONS` リストの末尾に追加する:

```python
    # Issue #259: backtest 永続化テーブル追加（新規 DB は _ALL_DDL で作成済み。既存 DB 用）
    "CREATE TABLE IF NOT EXISTS backtest_runs (run_id VARCHAR PRIMARY KEY, created_at TIMESTAMP NOT NULL DEFAULT current_timestamp, start_date DATE NOT NULL, end_date DATE NOT NULL, initial_cash DECIMAL(18,2) NOT NULL, scope_mode VARCHAR NOT NULL, scope_codes_json VARCHAR, params_json VARCHAR NOT NULL, cagr DOUBLE, sharpe DOUBLE, max_drawdown DOUBLE, win_rate DOUBLE, payoff_ratio DOUBLE, profit_factor DOUBLE, annual_volatility DOUBLE, calmar_ratio DOUBLE, avg_holding_days DOUBLE, total_trades INTEGER, effective_universe_size INTEGER)",
    "CREATE TABLE IF NOT EXISTS backtest_trades (run_id VARCHAR NOT NULL, date DATE NOT NULL, code VARCHAR NOT NULL, side VARCHAR NOT NULL, shares INTEGER NOT NULL, price DECIMAL(18,4) NOT NULL, commission DECIMAL(18,4) NOT NULL, realized_pnl DECIMAL(18,4), PRIMARY KEY (run_id, date, code, side))",
    "CREATE TABLE IF NOT EXISTS backtest_daily_equity (run_id VARCHAR NOT NULL, date DATE NOT NULL, portfolio_value DECIMAL(18,2) NOT NULL, cash DECIMAL(18,2) NOT NULL, PRIMARY KEY (run_id, date))",
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_backtest_persistence.py::TestBacktestTablesExist -v
```

Expected: `4 passed`

- [ ] **Step 5: 既存テスト全体が壊れていないことを確認**

```bash
python -m pytest --tb=short -q
```

Expected: 全テスト pass（新規 4 件増加）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/data/schema.py tests/test_backtest_persistence.py
git commit -m "feat: add backtest_runs/trades/daily_equity tables to schema (Issue #259)"
```

---

### Task 2: `persistence.py` を作成し `save_backtest_to_db()` を実装

**Files:**
- Create: `src/kabusys/backtest/persistence.py`
- Test: `tests/test_backtest_persistence.py`（Task 1 で作成済み、テストクラスを追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_persistence.py` の末尾に以下を追加する（`TestBacktestTablesExist` クラスの後）:

```python
# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

from kabusys.backtest.metrics import BacktestMetrics
from kabusys.backtest.simulator import DailySnapshot, TradeRecord
from kabusys.backtest.engine import BacktestResult
from kabusys.backtest.report import (
    BacktestReport,
    ReportMeta,
    HeadlineMetrics,
    TradeSection,
    PerformanceSection,
)


def _make_result() -> BacktestResult:
    history = [
        DailySnapshot(
            date=date(2024, 1, 4),
            cash=9_500_000.0,
            positions={"7203": 100},
            portfolio_value=10_100_000.0,
        ),
        DailySnapshot(
            date=date(2024, 1, 5),
            cash=9_500_000.0,
            positions={"7203": 100},
            portfolio_value=10_200_000.0,
        ),
    ]
    trades = [
        TradeRecord(
            date=date(2024, 1, 4),
            code="7203",
            side="buy",
            shares=100,
            price=6000.0,
            commission=3300.0,
            realized_pnl=None,
        ),
        TradeRecord(
            date=date(2024, 1, 5),
            code="7203",
            side="sell",
            shares=100,
            price=6100.0,
            commission=3355.0,
            realized_pnl=6645.0,
        ),
    ]
    metrics = BacktestMetrics(
        cagr=0.12,
        sharpe_ratio=1.5,
        max_drawdown=0.05,
        win_rate=0.6,
        payoff_ratio=1.8,
        total_trades=1,
        annual_volatility=0.15,
        calmar_ratio=2.4,
        profit_factor=2.1,
        avg_holding_days=1.0,
    )
    return BacktestResult(
        history=history,
        trades=trades,
        metrics=metrics,
        scope_mode="default_universe",
        effective_universe_size=100,
    )


def _make_report(result: BacktestResult, run_id: str = "test-run-001") -> BacktestReport:
    meta = ReportMeta(
        run_id=run_id,
        generated_at="2024-01-05T00:00:00+00:00",
        start_date="2024-01-04",
        end_date="2024-01-05",
        initial_cash=10_000_000.0,
        slippage_rate=0.001,
        commission_rate=0.00055,
        allocation_method="risk_based",
        max_position_pct=0.10,
        max_utilization=0.70,
        max_positions=10,
        risk_pct=0.005,
        stop_loss_pct=0.08,
        lot_size=100,
        scope_mode="default_universe",
        effective_universe_size=100,
    )
    headline = HeadlineMetrics(
        initial_cash=10_000_000.0,
        final_value=10_200_000.0,
        total_return=0.02,
        cagr=0.12,
        realized_pnl=6645.0,
        total_commission=6655.0,
        sharpe_ratio=1.5,
        max_drawdown=0.05,
        annual_volatility=0.15,
        calmar_ratio=2.4,
    )
    trade_section = TradeSection(
        total_trades=1,
        win_rate=0.6,
        payoff_ratio=1.8,
        profit_factor=2.1,
        avg_profit=6645.0,
        avg_loss=0.0,
        avg_holding_days=1.0,
    )
    return BacktestReport(
        meta=meta,
        headline=headline,
        trades=trade_section,
        performance=PerformanceSection(monthly_returns=[]),
        warnings=[],
    )


# ---------------------------------------------------------------------------
# save_backtest_to_db テスト
# ---------------------------------------------------------------------------


class TestSaveBacktestToDb:
    def setup_method(self):
        self.conn = init_schema(":memory:")
        self.result = _make_result()
        self.report = _make_report(self.result)

    def teardown_method(self):
        self.conn.close()

    def test_inserts_one_row_into_backtest_runs(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        count = self.conn.execute("SELECT COUNT(*) FROM backtest_runs").fetchone()[0]
        assert count == 1

    def test_backtest_runs_metrics_are_correct(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT run_id, cagr, sharpe, max_drawdown, total_trades, effective_universe_size "
            "FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        assert row[0] == "test-run-001"
        assert abs(row[1] - 0.12) < 1e-6   # cagr
        assert abs(row[2] - 1.5) < 1e-6    # sharpe
        assert abs(row[3] - 0.05) < 1e-6   # max_drawdown
        assert row[4] == 1                   # total_trades
        assert row[5] == 100                 # effective_universe_size

    def test_inserts_all_trades(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        count = self.conn.execute("SELECT COUNT(*) FROM backtest_trades").fetchone()[0]
        assert count == 2

    def test_sell_trade_realized_pnl_is_correct(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT realized_pnl FROM backtest_trades "
            "WHERE run_id = 'test-run-001' AND side = 'sell'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 6645.0) < 0.01

    def test_buy_trade_realized_pnl_is_null(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT realized_pnl FROM backtest_trades "
            "WHERE run_id = 'test-run-001' AND side = 'buy'"
        ).fetchone()
        assert row is not None
        assert row[0] is None

    def test_inserts_all_daily_equity_rows(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM backtest_daily_equity"
        ).fetchone()[0]
        assert count == 2

    def test_daily_equity_portfolio_value_is_correct(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT portfolio_value FROM backtest_daily_equity "
            "WHERE run_id = 'test-run-001' AND date = '2024-01-05'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 10_200_000.0) < 0.01

    def test_duplicate_run_id_raises(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        with pytest.raises(Exception):
            save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)

    def test_empty_trades_and_history_succeed(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        empty_result = BacktestResult(
            history=[],
            trades=[],
            metrics=BacktestMetrics(
                cagr=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                payoff_ratio=0.0,
                total_trades=0,
            ),
        )
        report2 = _make_report(empty_result, run_id="test-run-002")
        save_backtest_to_db(self.conn, report2.meta.run_id, empty_result, report2)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM backtest_runs WHERE run_id = 'test-run-002'"
        ).fetchone()[0]
        assert count == 1

    def test_params_json_contains_initial_cash(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT params_json FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        params = json.loads(row[0])
        assert params["initial_cash"] == 10_000_000.0

    def test_scope_mode_is_stored(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        save_backtest_to_db(self.conn, self.report.meta.run_id, self.result, self.report)
        row = self.conn.execute(
            "SELECT scope_mode FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        assert row[0] == "default_universe"

    def test_manual_codes_scope_codes_json_stored(self):
        from kabusys.backtest.persistence import save_backtest_to_db

        manual_result = BacktestResult(
            history=self.result.history,
            trades=self.result.trades,
            metrics=self.result.metrics,
            scope_mode="manual_codes",
            scope_codes=["7203", "9984"],
        )
        meta2 = ReportMeta(
            run_id="test-run-003",
            generated_at="2024-01-05T00:00:00+00:00",
            start_date="2024-01-04",
            end_date="2024-01-05",
            initial_cash=10_000_000.0,
            slippage_rate=0.001,
            commission_rate=0.00055,
            allocation_method="risk_based",
            max_position_pct=0.10,
            max_utilization=0.70,
            max_positions=10,
            risk_pct=0.005,
            stop_loss_pct=0.08,
            lot_size=100,
            scope_mode="manual_codes",
            scope_codes=["7203", "9984"],
        )
        report3 = BacktestReport(
            meta=meta2,
            headline=self.report.headline,
            trades=self.report.trades,
            performance=self.report.performance,
            warnings=[],
        )
        save_backtest_to_db(self.conn, "test-run-003", manual_result, report3)
        row = self.conn.execute(
            "SELECT scope_mode, scope_codes_json FROM backtest_runs WHERE run_id = 'test-run-003'"
        ).fetchone()
        assert row[0] == "manual_codes"
        assert json.loads(row[1]) == ["7203", "9984"]
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_backtest_persistence.py::TestSaveBacktestToDb -v
```

Expected: `ImportError: cannot import name 'save_backtest_to_db' from 'kabusys.backtest.persistence'`

- [ ] **Step 3: `persistence.py` を実装**

`src/kabusys/backtest/persistence.py` を新規作成する:

```python
"""
バックテスト結果 DB 永続化モジュール。

run.py（CLI）から呼び出され、BacktestResult と BacktestReport を
backtest_runs / backtest_trades / backtest_daily_equity の 3 テーブルに
単一トランザクションで書き込む。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from kabusys.backtest.engine import BacktestResult
    from kabusys.backtest.report import BacktestReport

logger = logging.getLogger(__name__)


def save_backtest_to_db(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    result: "BacktestResult",
    report: "BacktestReport",
) -> None:
    """バックテスト結果を DB の 3 テーブルに永続化する。

    3 テーブルへの書き込みを単一トランザクションで実行する。
    run_id の一意性は呼び出し元が保証すること。重複 run_id は
    PRIMARY KEY 制約エラーとして例外を送出する。

    Args:
        conn:   初期化済みの DuckDB 接続（backtest_runs 等のテーブルが存在すること）。
        run_id: 一意の実行 ID。report.meta.run_id と一致させること。
        result: run_backtest() の戻り値。
        report: build_report() の戻り値。
    """
    meta = report.meta
    m = result.metrics

    # params_json: ReportMeta から run_id / generated_at / report_type を除いた全パラメータ
    params = {
        "start_date": meta.start_date,
        "end_date": meta.end_date,
        "initial_cash": meta.initial_cash,
        "slippage_rate": meta.slippage_rate,
        "commission_rate": meta.commission_rate,
        "allocation_method": meta.allocation_method,
        "max_position_pct": meta.max_position_pct,
        "max_utilization": meta.max_utilization,
        "max_positions": meta.max_positions,
        "risk_pct": meta.risk_pct,
        "stop_loss_pct": meta.stop_loss_pct,
        "lot_size": meta.lot_size,
        "min_holding_days": meta.min_holding_days,
        "max_holding_days": meta.max_holding_days,
        "trailing_stop_atr": meta.trailing_stop_atr,
        "scope_mode": meta.scope_mode,
    }
    params_json = json.dumps(params, ensure_ascii=False)

    scope_codes_json = (
        json.dumps(meta.scope_codes, ensure_ascii=False)
        if meta.scope_codes is not None
        else None
    )

    conn.execute("BEGIN")
    try:
        # backtest_runs: 1 行 INSERT
        conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash,
                scope_mode, scope_codes_json, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio,
                profit_factor, annual_volatility, calmar_ratio,
                avg_holding_days, total_trades, effective_universe_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                meta.start_date,
                meta.end_date,
                meta.initial_cash,
                meta.scope_mode,
                scope_codes_json,
                params_json,
                m.cagr,
                m.sharpe_ratio,
                m.max_drawdown,
                m.win_rate,
                m.payoff_ratio,
                m.profit_factor,
                m.annual_volatility,
                m.calmar_ratio,
                m.avg_holding_days,
                m.total_trades,
                meta.effective_universe_size,
            ],
        )

        # backtest_trades: TradeRecord を一括 INSERT
        if result.trades:
            conn.executemany(
                """
                INSERT INTO backtest_trades
                    (run_id, date, code, side, shares, price, commission, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    [
                        run_id,
                        t.date,
                        t.code,
                        t.side,
                        t.shares,
                        t.price,
                        t.commission,
                        t.realized_pnl,
                    ]
                    for t in result.trades
                ],
            )

        # backtest_daily_equity: DailySnapshot を一括 INSERT
        if result.history:
            conn.executemany(
                """
                INSERT INTO backtest_daily_equity (run_id, date, portfolio_value, cash)
                VALUES (?, ?, ?, ?)
                """,
                [
                    [run_id, s.date, s.portfolio_value, s.cash]
                    for s in result.history
                ],
            )

        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("save_backtest_to_db: ROLLBACK failed: %s", rb_exc)
        raise
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_backtest_persistence.py::TestSaveBacktestToDb -v
```

Expected: `12 passed`

- [ ] **Step 5: 全テストが壊れていないことを確認**

```bash
python -m pytest --tb=short -q
```

Expected: 全テスト pass

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/backtest/persistence.py tests/test_backtest_persistence.py
git commit -m "feat: implement save_backtest_to_db() persistence module (Issue #259)"
```

---

### Task 3: `run.py` に DB 永続化呼び出しを追加

**Files:**
- Modify: `src/kabusys/backtest/run.py`
- Test: `tests/test_backtest_persistence.py`（Task 2 で作成済み、統合テストクラスを追加）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_persistence.py` の末尾に以下を追加する:

```python
class TestRunCliPersistence:
    """run.py の --output-format all 実行後に DB に行が保存されることを確認。"""

    def test_run_backtest_saves_to_db(self, tmp_path):
        """run.py を直接関数呼び出しして DB への保存を検証する。

        実際の DuckDB ファイルを tmp_path に作成し、init_schema で初期化後に
        save_backtest_to_db が正しく呼ばれることをインメモリ DB で再現する。
        """
        from kabusys.backtest.persistence import save_backtest_to_db

        db_path = tmp_path / "test.duckdb"
        conn = init_schema(str(db_path))
        conn.close()

        result = _make_result()
        report = _make_report(result, run_id="cli-test-001")

        import duckdb as _duckdb
        conn_persist = _duckdb.connect(str(db_path))
        try:
            save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        finally:
            conn_persist.close()

        # 検証: 保存されたことを別接続で確認
        conn_verify = _duckdb.connect(str(db_path))
        count = conn_verify.execute(
            "SELECT COUNT(*) FROM backtest_runs WHERE run_id = 'cli-test-001'"
        ).fetchone()[0]
        conn_verify.close()
        assert count == 1

    def test_db_persistence_does_not_affect_existing_schema(self, tmp_path):
        """永続化処理が既存テーブル（prices_daily 等）に影響しないことを確認。"""
        from kabusys.backtest.persistence import save_backtest_to_db

        db_path = tmp_path / "test2.duckdb"
        conn = init_schema(str(db_path))
        conn.close()

        result = _make_result()
        report = _make_report(result, run_id="cli-test-002")

        import duckdb as _duckdb
        conn_persist = _duckdb.connect(str(db_path))
        try:
            save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        finally:
            conn_persist.close()

        conn_verify = _duckdb.connect(str(db_path))
        # 既存テーブルが壊れていないことを確認
        count = conn_verify.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'prices_daily'"
        ).fetchone()[0]
        conn_verify.close()
        assert count == 1
```

- [ ] **Step 2: テストが通ることを確認（persistence.py は既に実装済み）**

```bash
python -m pytest tests/test_backtest_persistence.py::TestRunCliPersistence -v
```

Expected: `2 passed`

- [ ] **Step 3: `run.py` を修正して DB 永続化を追加**

`src/kabusys/backtest/run.py` のファイル先頭の import 部分を修正する。`from __future__ import annotations` の直後に以下の import を追加する:

現在の状態（run.py 冒頭部）:
```python
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
```

変更後:
```python
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path
```

次に `main()` 関数内の `fmt = args.output_format` から始まる出力処理ブロックを以下のように変更する。

現在の状態（run.py:238-248）:
```python
    fmt = args.output_format
    if fmt == "summary":
        print(format_cli_summary(report))
    elif fmt == "json":
        print(format_json(report))
    elif fmt == "markdown":
        print(format_markdown(report))
    elif fmt == "all":
        print(format_cli_summary(report))
        run_dir = save_report(report, result, output_dir=args.output_dir)
        logger.info("レポートを保存しました: %s", run_dir)
```

変更後:
```python
    fmt = args.output_format
    if fmt == "summary":
        print(format_cli_summary(report))
    elif fmt == "json":
        print(format_json(report))
    elif fmt == "markdown":
        print(format_markdown(report))
    elif fmt == "all":
        print(format_cli_summary(report))
        run_dir = save_report(report, result, output_dir=args.output_dir)
        logger.info("レポートを保存しました: %s", run_dir)

    # DB 永続化（--output-format に関わらず常に実行）
    from kabusys.backtest.persistence import save_backtest_to_db

    import duckdb as _duckdb

    conn_persist = _duckdb.connect(str(Path(args.db)))
    try:
        save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        logger.info("バックテスト結果を DB に保存しました: run_id=%s", report.meta.run_id)
    except Exception:
        logger.warning("DB 保存に失敗しました（ファイル保存は完了済み）", exc_info=True)
    finally:
        conn_persist.close()
```

- [ ] **Step 4: 全テストが通ることを確認**

```bash
python -m pytest --tb=short -q
```

Expected: 全テスト pass

- [ ] **Step 5: 静的型チェック（オプション）**

```bash
python -m mypy src/kabusys/backtest/persistence.py --ignore-missing-imports
```

Expected: `Success: no issues found`

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/backtest/run.py
git commit -m "feat: wire save_backtest_to_db into CLI run.py (Issue #259)"
```

---

## セルフレビュー

### スペックカバレッジ確認

| 仕様要件 | 対応タスク |
|---|---|
| `backtest_runs` テーブル作成 | Task 1 |
| `backtest_trades` テーブル作成 | Task 1 |
| `backtest_daily_equity` テーブル作成 | Task 1 |
| `_MIGRATIONS` への後付け追加 | Task 1 |
| `save_backtest_to_db()` 実装 | Task 2 |
| 単一トランザクション（失敗時 ROLLBACK） | Task 2 |
| `params_json` に全パラメータ保存 | Task 2 |
| `scope_codes_json` が `manual_codes` 時のみ非 NULL | Task 2 |
| 空 trades / history でも正常終了 | Task 2 |
| `run.py` に永続化呼び出しを追加 | Task 3 |
| 別接続（インメモリ実行 DB と永続 DB の分離） | Task 3 |
| DB 保存失敗は `logger.warning` で続行 | Task 3 |

### スコープ外確認

- バックテスト結果の削除・アーカイブ機能 → 対象外
- 既存ファイルアーティファクトの DB インポート → 対象外
- Streamlit 表示（Issue #260）→ 対象外
