# tests/test_signal_queue_report.py
"""signal_queue_report のユニットテスト"""

from __future__ import annotations

import json as json_mod
from datetime import date

import duckdb
import pytest

from kabusys.operations.signal_queue_report import (
    SignalQueueReport,
    _generate_warnings,
    build_report,
    collect_signals,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)

TARGET_DATE = date(2026, 4, 28)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """signal_queue テーブルを持つインメモリ DuckDB 接続。"""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signal_queue (
            signal_id   VARCHAR     NOT NULL PRIMARY KEY,
            date        DATE        NOT NULL,
            code        VARCHAR     NOT NULL,
            side        VARCHAR     NOT NULL CHECK (side IN ('buy', 'sell')),
            size        BIGINT      NOT NULL CHECK (size > 0),
            order_type  VARCHAR     NOT NULL CHECK (order_type IN ('market', 'limit', 'stop')),
            price       DECIMAL(18,4),
            status      VARCHAR     NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','processing','filled','cancelled','error','failed')),
            created_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp,
            processed_at TIMESTAMP
        )
    """)
    yield conn
    conn.close()


def _sig(conn, d, code, side, size=100, status="pending"):
    signal_id = f"TEST_{d}_{code}_{side}"
    conn.execute(
        """INSERT INTO signal_queue
               (signal_id, date, code, side, size, order_type, status)
           VALUES (?, ?, ?, ?, ?, 'market', ?)""",
        [signal_id, d, code, side, size, status],
    )


# ---------------------------------------------------------------------------
# collect_signals
# ---------------------------------------------------------------------------


def test_collect_signals_empty(db):
    assert collect_signals(db, TARGET_DATE) == []


def test_collect_signals_buy_and_sell(db):
    _sig(db, TARGET_DATE, "7203", "buy", size=100)
    _sig(db, TARGET_DATE, "9984", "sell", size=50)

    result = collect_signals(db, TARGET_DATE)
    assert len(result) == 2
    # code 昇順で返る
    assert result[0]["code"] == "7203"
    assert result[0]["side"] == "buy"
    assert result[0]["target_size"] == 100
    assert result[0]["target_weight"] is None   # signal_queue には存在しない
    assert result[0]["signal_rank"] is None     # signal_queue には存在しない


def test_collect_signals_only_pending(db):
    """status='pending' のみ取得され、filled/cancelled は除外される。"""
    _sig(db, TARGET_DATE, "7203", "buy", status="pending")
    _sig(db, TARGET_DATE, "9984", "buy", status="filled")
    _sig(db, TARGET_DATE, "1111", "buy", status="cancelled")
    result = collect_signals(db, TARGET_DATE)
    assert len(result) == 1
    assert result[0]["code"] == "7203"


def test_collect_signals_filters_by_date(db):
    """対象日以外のシグナルは取得されない。"""
    _sig(db, date(2026, 4, 27), "7203", "buy")
    assert collect_signals(db, TARGET_DATE) == []


def test_collect_signals_sorted_by_code(db):
    """code 昇順・side 昇順で返される。"""
    _sig(db, TARGET_DATE, "9999", "buy")
    _sig(db, TARGET_DATE, "1111", "buy")
    _sig(db, TARGET_DATE, "5555", "buy")
    result = collect_signals(db, TARGET_DATE)
    assert [r["code"] for r in result] == ["1111", "5555", "9999"]


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_empty():
    w = _generate_warnings(signals=[], total_count=0)
    assert len(w) == 1
    assert "シグナルがありません" in w[0]


def test_generate_warnings_ready_no_warnings():
    sigs = [
        {
            "code": "7203",
            "side": "buy",
            "target_size": 100,
            "target_weight": 0.05,
            "signal_rank": 1,
        }
    ]
    assert _generate_warnings(signals=sigs, total_count=1) == []


def test_generate_warnings_buy_no_size():
    sigs = [
        {
            "code": "7203",
            "side": "buy",
            "target_size": None,
            "target_weight": 0.05,
            "signal_rank": 1,
        }
    ]
    w = _generate_warnings(signals=sigs, total_count=1)
    assert any("7203" in warning for warning in w)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_ready():
    sigs = [
        {
            "code": "7203",
            "side": "buy",
            "target_size": 100,
            "target_weight": 0.05,
            "signal_rank": 1,
        },
        {
            "code": "9984",
            "side": "sell",
            "target_size": 50,
            "target_weight": 0.03,
            "signal_rank": 2,
        },
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    assert report.status == "READY"
    assert report.total_count == 2
    assert report.buy_count == 1
    assert report.sell_count == 1
    assert report.report_date == "2026-04-28"


def test_build_report_empty():
    report = build_report([], report_date=TARGET_DATE)
    assert report.status == "EMPTY"
    assert report.total_count == 0
    assert report.buy_count == 0
    assert report.sell_count == 0
    assert len(report.warnings) > 0


def test_build_report_generated_at_utc():
    report = build_report([], report_date=TARGET_DATE)
    assert "+00:00" in report.generated_at


def test_build_report_counts_correctly():
    sigs = [
        {
            "code": "1111",
            "side": "buy",
            "target_size": 100,
            "target_weight": 0.05,
            "signal_rank": 1,
        },
        {
            "code": "2222",
            "side": "buy",
            "target_size": 200,
            "target_weight": 0.10,
            "signal_rank": 2,
        },
        {
            "code": "3333",
            "side": "sell",
            "target_size": 50,
            "target_weight": 0.03,
            "signal_rank": 3,
        },
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    assert report.buy_count == 2
    assert report.sell_count == 1
    assert report.total_count == 3


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_ready():
    sigs = [
        {
            "code": "7203",
            "side": "buy",
            "target_size": 100,
            "target_weight": 0.05,
            "signal_rank": 1,
        }
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "READY" in s
    assert "2026-04-28" in s
    assert "7203" in s


def test_format_cli_summary_empty_shows_warning():
    report = build_report([], report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "EMPTY" in s
    assert "Warnings" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable():
    report = build_report([], report_date=TARGET_DATE)
    data = json_mod.loads(format_json(report))
    for key in (
        "status",
        "report_date",
        "generated_at",
        "total_count",
        "buy_count",
        "sell_count",
        "signals",
        "warnings",
    ):
        assert key in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_ready_has_signal_table():
    sigs = [
        {
            "code": "7203",
            "side": "buy",
            "target_size": 100,
            "target_weight": 0.05,
            "signal_rank": 1,
        }
    ]
    report = build_report(sigs, report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Signal Queue Confirmation" in md
    assert "Signal 一覧" in md
    assert "7203" in md
    assert "5.0%" in md


def test_format_markdown_empty_no_signal_table():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "EMPTY" in md
    assert "Signal 一覧" not in md


def test_format_markdown_final_decision_section():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Final Decision" in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_three_files(tmp_path):
    report = build_report([], report_date=TARGET_DATE)
    dest = save_report(report, output_dir=tmp_path)
    assert (dest / "summary.json").exists()
    assert (dest / "report.md").exists()
    assert (dest / "warnings.json").exists()


def test_save_report_invalid_format_raises(tmp_path):
    report = SignalQueueReport(
        report_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status="EMPTY",
        total_count=0,
        buy_count=0,
        sell_count=0,
        signals=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_impossible_calendar_date_raises(tmp_path):
    report = SignalQueueReport(
        report_date="2026-02-30",
        generated_at="2026-04-27T00:00:00+00:00",
        status="EMPTY",
        total_count=0,
        buy_count=0,
        sell_count=0,
        signals=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_idempotent(tmp_path):
    report = build_report([], report_date=TARGET_DATE)
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)
    assert (tmp_path / "2026-04-28" / "summary.json").exists()
