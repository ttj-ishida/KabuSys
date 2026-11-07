"""scripts/run_performance_record.py のテスト（Issue #427）。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_performance_record  # noqa: E402

from kabusys.data.schema import init_schema  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    c = init_schema(tmp_path / "t.duckdb")
    yield c
    c.close()


def _settings(*, manual=False, env="paper_trading"):
    s = MagicMock()
    s.manual_trading_enabled = manual
    s.manual_trading_initial_cash = 3_000_000.0
    s.env = env
    s.is_live = env == "live"
    s.is_paper = env == "paper_trading"
    s.is_dev = env == "development"
    return s


def _count(conn):
    return conn.execute("SELECT COUNT(*) FROM portfolio_performance").fetchone()[0]


def test_manual_mode_records_manual_portfolio_value(conn):
    d = date(2026, 11, 6)  # 金曜
    with patch.object(
        run_performance_record,
        "calc_manual_portfolio_value",
        return_value=(3_100_000.0, 500_000.0),
    ) as m:
        status = run_performance_record.record_for_date(_settings(manual=True), conn, d)
    assert status == "recorded"
    assert m.call_args.args[1] == 3_000_000.0
    assert m.call_args.kwargs["as_of"] == d
    rows = conn.execute("SELECT env, equity, cash FROM portfolio_performance").fetchall()
    assert [(r[0], float(r[1]), float(r[2])) for r in rows] == [
        ("paper_trading", 3_100_000.0, 500_000.0)
    ]


def test_paper_mode_uses_paper_calc(conn):
    d = date(2026, 11, 6)
    with patch.object(
        run_performance_record,
        "calc_paper_portfolio_value",
        return_value=(1_200_000.0, 200_000.0),
    ):
        status = run_performance_record.record_for_date(_settings(), conn, d)
    assert status == "recorded"
    assert _count(conn) == 1


def test_live_mode_does_nothing(conn):
    with patch.object(run_performance_record, "calc_paper_portfolio_value") as paper:
        status = run_performance_record.record_for_date(
            _settings(env="live"), conn, date(2026, 11, 6)
        )
    assert status == "skipped_live"
    assert _count(conn) == 0
    paper.assert_not_called()


def test_non_trading_day_does_nothing(conn):
    with patch.object(run_performance_record, "calc_paper_portfolio_value") as paper:
        status = run_performance_record.record_for_date(
            _settings(),
            conn,
            date(2026, 11, 7),  # 土曜
        )
    assert status == "skipped_non_trading_day"
    assert _count(conn) == 0
    paper.assert_not_called()
