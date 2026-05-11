"""position_reconciliation_report のユニットテスト"""

from __future__ import annotations

import json as json_mod
import sqlite3
from datetime import date, datetime, timezone

import pytest

from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_record import OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.operations.position_reconciliation_report import (
    ENTRY_MATCH,
    ENTRY_MISMATCH,
    STATUS_CLEAN,
    STATUS_DISCREPANCY,
    PositionEntry,
    PositionReconciliationReport,
    _generate_warnings,
    build_report,
    collect_position_snapshot,
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
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture()
def repo(conn):
    return OrderRepository(conn)


def _insert_order(
    repo: OrderRepository,
    code: str,
    side: str,
    qty: int,
    cid: str,
    state: OrderState = OrderState.Filled,
    filled_qty: int | None = None,
) -> None:
    """指定状態の注文を DB に挿入するヘルパー。"""
    record = OrderRecord(
        client_order_id=cid,
        signal_id=f"sig_{cid}",
        code=code,
        side=side,
        qty=qty,
        order_type="limit",
        price=1500.0,
        state=state,
        filled_qty=filled_qty if filled_qty is not None else qty,
        broker_order_id=f"BRK_{cid}",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    repo.save(record)


# ---------------------------------------------------------------------------
# collect_position_snapshot
# ---------------------------------------------------------------------------


def test_collect_empty_returns_empty_list(repo):
    broker = MockBrokerClient()
    assert collect_position_snapshot(broker, repo) == []


def test_collect_broker_only_is_mismatch(repo):
    """broker のみ保有（local 注文なし）→ MISMATCH, diff=broker_qty"""
    broker = MockBrokerClient(initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)])
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].code == "7203"
    assert result[0].broker_qty == 100
    assert result[0].local_qty == 0
    assert result[0].diff == 100
    assert result[0].status == ENTRY_MISMATCH


def test_collect_local_only_is_mismatch(repo):
    """local に Filled 注文あり、broker に未反映 → MISMATCH, diff 負"""
    broker = MockBrokerClient()
    _insert_order(repo, "9984", "buy", 50, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].code == "9984"
    assert result[0].broker_qty == 0
    assert result[0].local_qty == 50
    assert result[0].diff == -50
    assert result[0].status == ENTRY_MISMATCH


def test_collect_matching_position_is_match(repo):
    """broker と local が一致 → MATCH, diff=0"""
    broker = MockBrokerClient(initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)])
    _insert_order(repo, "7203", "buy", 100, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].status == ENTRY_MATCH
    assert result[0].diff == 0


def test_collect_qty_mismatch(repo):
    """broker=100, local Filled=80 → MISMATCH, diff=+20"""
    broker = MockBrokerClient(initial_positions=[Position(code="7203", qty=100, avg_price=1500.0)])
    _insert_order(repo, "7203", "buy", 80, "ord-001")
    result = collect_position_snapshot(broker, repo)
    assert result[0].broker_qty == 100
    assert result[0].local_qty == 80
    assert result[0].diff == 20
    assert result[0].status == ENTRY_MISMATCH


def test_collect_multiple_codes(repo):
    """複数銘柄: 一致・不一致の混在"""
    broker = MockBrokerClient(
        initial_positions=[
            Position(code="1111", qty=100, avg_price=1000.0),
            Position(code="2222", qty=50, avg_price=2000.0),
        ]
    )
    _insert_order(repo, "1111", "buy", 100, "ord-001")  # MATCH
    _insert_order(repo, "2222", "buy", 30, "ord-002")  # MISMATCH
    result = collect_position_snapshot(broker, repo)
    codes = [e.code for e in result]
    assert "1111" in codes
    assert "2222" in codes
    assert next(e for e in result if e.code == "1111").status == ENTRY_MATCH
    assert next(e for e in result if e.code == "2222").status == ENTRY_MISMATCH


def test_collect_sorted_by_code(repo):
    """結果は code 昇順でソートされる"""
    broker = MockBrokerClient(
        initial_positions=[
            Position(code="9999", qty=10, avg_price=100.0),
            Position(code="1111", qty=10, avg_price=100.0),
            Position(code="5555", qty=10, avg_price=100.0),
        ]
    )
    result = collect_position_snapshot(broker, repo)
    assert [e.code for e in result] == ["1111", "5555", "9999"]


def test_collect_partial_fill_counts(repo):
    """PartialFill の filled_qty がローカル数量に反映される"""
    broker = MockBrokerClient()
    _insert_order(
        repo,
        "7203",
        "buy",
        100,
        "ord-001",
        state=OrderState.PartialFill,
        filled_qty=50,
    )
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].local_qty == 50


def test_collect_sell_reduces_local_qty(repo):
    """buy Filled 100 - sell Filled 30 → local_qty=70"""
    broker = MockBrokerClient()
    _insert_order(repo, "7203", "buy", 100, "ord-001")
    _insert_order(repo, "7203", "sell", 30, "ord-002")
    result = collect_position_snapshot(broker, repo)
    assert len(result) == 1
    assert result[0].local_qty == 70


def test_collect_skips_non_filled_states(repo):
    """OrderCreated は local 集計に含まない"""
    broker = MockBrokerClient()
    _insert_order(
        repo,
        "7203",
        "buy",
        100,
        "ord-001",
        state=OrderState.OrderCreated,
        filled_qty=0,
    )
    result = collect_position_snapshot(broker, repo)
    assert result == []


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_clean():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH)
    ]
    assert _generate_warnings(entries) == []


def test_generate_warnings_mismatch_contains_code():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH)
    ]
    warnings = _generate_warnings(entries)
    assert len(warnings) == 1
    assert "7203" in warnings[0]
    assert "100" in warnings[0]
    assert "80" in warnings[0]


def test_generate_warnings_multiple_mismatch():
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH),
        PositionEntry(code="2222", broker_qty=0, local_qty=50, diff=-50, status=ENTRY_MISMATCH),
    ]
    assert len(_generate_warnings(entries)) == 2


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_clean_status():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH)
    ]
    assert build_report(entries, report_date=TARGET_DATE).status == STATUS_CLEAN


def test_build_report_discrepancy_status():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH)
    ]
    assert build_report(entries, report_date=TARGET_DATE).status == STATUS_DISCREPANCY


def test_build_report_counts():
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH),
        PositionEntry(code="2222", broker_qty=50, local_qty=30, diff=20, status=ENTRY_MISMATCH),
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    assert report.total_count == 2
    assert report.match_count == 1
    assert report.mismatch_count == 1


def test_build_report_generated_at_utc():
    report = build_report([], report_date=TARGET_DATE)
    assert "+00:00" in report.generated_at


def test_build_report_empty_entries_is_clean():
    report = build_report([], report_date=TARGET_DATE)
    assert report.status == STATUS_CLEAN
    assert report.total_count == 0
    assert report.warnings == []


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_clean_no_mark():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert STATUS_CLEAN in s
    assert "2026-04-28" in s
    assert "[!]" not in s


def test_format_cli_discrepancy_shows_mark():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert STATUS_DISCREPANCY in s
    assert "[!]" in s


def test_format_cli_shows_all_positions():
    """MATCH 銘柄も出力に含まれる"""
    entries = [
        PositionEntry(code="1111", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH),
        PositionEntry(code="2222", broker_qty=50, local_qty=30, diff=20, status=ENTRY_MISMATCH),
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    s = format_cli_summary(report)
    assert "1111" in s
    assert "2222" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    data = json_mod.loads(format_json(report))
    for key in (
        "status",
        "report_date",
        "generated_at",
        "total_count",
        "match_count",
        "mismatch_count",
        "positions",
        "warnings",
    ):
        assert key in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_required_sections():
    report = build_report([], report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "Position Reconciliation" in md
    assert "Overview" in md
    assert "Final Decision" in md


def test_format_markdown_warnings_only_when_discrepancy():
    clean_entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=100, diff=0, status=ENTRY_MATCH)
    ]
    assert "Warnings" not in format_markdown(build_report(clean_entries, report_date=TARGET_DATE))
    disc_entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH)
    ]
    assert "Warnings" in format_markdown(build_report(disc_entries, report_date=TARGET_DATE))


def test_format_markdown_position_table():
    entries = [
        PositionEntry(code="7203", broker_qty=100, local_qty=80, diff=20, status=ENTRY_MISMATCH)
    ]
    report = build_report(entries, report_date=TARGET_DATE)
    md = format_markdown(report)
    assert "7203" in md
    assert "ポジション一覧" in md


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
    report = PositionReconciliationReport(
        report_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status=STATUS_CLEAN,
        total_count=0,
        match_count=0,
        mismatch_count=0,
        positions=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_impossible_calendar_date_raises(tmp_path):
    report = PositionReconciliationReport(
        report_date="2026-02-30",
        generated_at="2026-04-27T00:00:00+00:00",
        status=STATUS_CLEAN,
        total_count=0,
        match_count=0,
        mismatch_count=0,
        positions=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_idempotent(tmp_path):
    report = build_report([], report_date=TARGET_DATE)
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)
    assert (tmp_path / "2026-04-28" / "summary.json").exists()
