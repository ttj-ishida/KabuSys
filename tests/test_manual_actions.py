"""manual_action_queue（手動売却候補）のテスト"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from kabusys.operations.manual_trades import (
    ensure_manual_action_schema,
    list_manual_actions,
    record_sell_candidates,
    update_manual_action_status,
)

D = date(2026, 10, 8)


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    ensure_manual_action_schema(c)
    yield c
    c.close()


def _sig(code, reason="stop_loss", qty=100, source="manual"):
    return {"code": code, "score": 0.1, "reason": reason, "qty": qty, "source": source}


def test_records_only_manual_and_mixed(conn):
    n = record_sell_candidates(
        conn, D, [_sig("A", source="manual"), _sig("B", source="mixed"), _sig("C", source="auto")]
    )
    assert n == 2
    actions = list_manual_actions(conn, target_date=D)
    assert [(a.action_id, a.code, a.action, a.status) for a in actions] == [
        ("2026-10-08_A_sell_candidate", "A", "sell_candidate", "open"),
        ("2026-10-08_B_sell_candidate", "B", "sell_candidate", "open"),
    ]


def test_rerecord_updates_reason_and_keeps_status(conn):
    record_sell_candidates(conn, D, [_sig("A", reason="score_drop", qty=100)])
    update_manual_action_status(conn, "2026-10-08_A_sell_candidate", "done")

    record_sell_candidates(conn, D, [_sig("A", reason="stop_loss", qty=200)])

    [action] = list_manual_actions(conn, target_date=D)
    assert action.status == "done"
    assert action.reason == "stop_loss"
    assert action.qty == 200
    assert action.updated_at is not None


def test_list_filters_by_status(conn):
    record_sell_candidates(conn, D, [_sig("A"), _sig("B")])
    update_manual_action_status(conn, "2026-10-08_B_sell_candidate", "skipped")
    assert [a.code for a in list_manual_actions(conn, status="open")] == ["A"]


def test_update_rejects_unknown_status(conn):
    record_sell_candidates(conn, D, [_sig("A")])
    with pytest.raises(ValueError):
        update_manual_action_status(conn, "2026-10-08_A_sell_candidate", "sold")


def test_init_schema_creates_manual_action_queue():
    from kabusys.data.schema import init_schema

    c = init_schema(":memory:")
    row = c.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'manual_action_queue'"
    ).fetchone()
    assert row[0] == 1


def test_execution_package_never_references_manual_action_queue():
    """Execution Engine 側が手動売却候補を発注対象として読まないこと。"""
    import kabusys.execution as execution_pkg

    pkg_dir = Path(execution_pkg.__file__).parent
    offenders = [
        p.name
        for p in pkg_dir.rglob("*.py")
        if "manual_action_queue" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
