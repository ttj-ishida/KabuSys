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
