# tests/test_signal_queue_status.py
"""signal_queue_status（SQLite）モジュールのテスト（Issue #413）。"""

from __future__ import annotations

import sqlite3
from datetime import date

import duckdb
import pytest

from kabusys.execution import signal_queue_status as sqs
from kabusys.execution.order_record import OrderState

SIGNAL_DATE = date(2026, 3, 27)


@pytest.fixture
def sconn():
    c = sqlite3.connect(":memory:")
    sqs.ensure_schema(c)
    yield c
    c.close()


@pytest.fixture
def dconn():
    c = duckdb.connect(":memory:")
    c.execute("""
        CREATE TABLE signal_queue (
            signal_id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            size BIGINT NOT NULL,
            order_type VARCHAR NOT NULL,
            price DECIMAL(18,4),
            status VARCHAR NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            processed_at TIMESTAMP
        )
    """)
    yield c
    c.close()


def _rec(conn, qid, status, *, code="1234", side="buy", client_order_id=None, reason=None):
    sqs.record(
        conn,
        queue_signal_id=qid,
        signal_date=SIGNAL_DATE,
        code=code,
        side=side,
        status=status,
        reason=reason,
        client_order_id=client_order_id,
    )


class TestSchema:
    def test_ensure_schema_is_idempotent(self, sconn):
        sqs.ensure_schema(sconn)
        cols = {r[1] for r in sconn.execute("PRAGMA table_info(signal_queue_status)")}
        assert {
            "queue_signal_id",
            "business_key",
            "signal_date",
            "code",
            "side",
            "status",
            "reason",
            "client_order_id",
            "updated_at",
        } <= cols

    def test_invalid_status_rejected(self, sconn):
        with pytest.raises(sqlite3.IntegrityError):
            _rec(sconn, "q1", "error")

    def test_business_key_format(self):
        assert sqs.business_key(SIGNAL_DATE, "1234", "buy") == "2026-03-27_1234_buy"


class TestRecordAndRead:
    def test_record_upserts_and_keeps_client_order_id(self, sconn):
        _rec(sconn, "q1", "processing", client_order_id="coid-1")
        _rec(sconn, "q1", "filled")
        row = sconn.execute(
            "SELECT status, client_order_id, business_key, signal_date FROM signal_queue_status"
        ).fetchone()
        assert tuple(row) == ("filled", "coid-1", "2026-03-27_1234_buy", "2026-03-27")

    def test_get_statuses_filters_by_signal_date(self, sconn):
        _rec(sconn, "q1", "processing")
        sqs.record(
            sconn,
            queue_signal_id="other",
            signal_date=date(2026, 3, 26),
            code="1234",
            side="buy",
            status="filled",
        )
        assert sqs.get_statuses(sconn, SIGNAL_DATE) == {"q1": "processing"}

    def test_get_statuses_missing_table_returns_empty(self):
        c = sqlite3.connect(":memory:")
        assert sqs.get_statuses(c, SIGNAL_DATE) == {}

    def test_register_pending_does_not_overwrite(self, sconn):
        _rec(sconn, "q1", "processing")
        sqs.register_pending(
            sconn, queue_signal_id="q1", signal_date=SIGNAL_DATE, code="1234", side="buy"
        )
        sqs.register_pending(
            sconn, queue_signal_id="q2", signal_date=SIGNAL_DATE, code="5678", side="buy"
        )
        assert sqs.get_statuses(sconn, SIGNAL_DATE) == {"q1": "processing", "q2": "pending"}

    def test_update_by_client_order_id(self, sconn):
        _rec(sconn, "q1", "processing", client_order_id="coid-1")
        _rec(sconn, "q2", "processing", client_order_id="coid-2")
        n = sqs.update_by_client_order_id(sconn, "coid-1", "failed", reason="rejected")
        assert n == 1
        rows = dict(sconn.execute("SELECT queue_signal_id, status FROM signal_queue_status"))
        assert rows == {"q1": "failed", "q2": "processing"}
        reason = sconn.execute(
            "SELECT reason FROM signal_queue_status WHERE queue_signal_id='q1'"
        ).fetchone()[0]
        assert reason == "rejected"

    def test_count_by_status(self, sconn):
        _rec(sconn, "q1", "pending")
        _rec(sconn, "q2", "filled", code="5678")
        _rec(sconn, "q3", "filled", code="9012")
        assert sqs.count_by_status(sconn, SIGNAL_DATE, "pending") == 1
        assert sqs.count_by_status(sconn, SIGNAL_DATE, "filled") == 2
        assert sqs.count_by_status(sconn, date(2026, 3, 30), "filled") == 0

    def test_count_by_status_missing_table_returns_zero(self):
        c = sqlite3.connect(":memory:")
        assert sqs.count_by_status(c, SIGNAL_DATE, "pending") == 0


class TestStatusForOrderState:
    @pytest.mark.parametrize(
        "state, expected",
        [
            (OrderState.Filled, ("filled", None)),
            (OrderState.Closed, ("filled", None)),
            (OrderState.Rejected, ("failed", "rejected")),
            (OrderState.Cancelled, ("cancelled", "cancelled")),
            (OrderState.OrderAccepted, ("processing", None)),
            (OrderState.PartialFill, ("processing", None)),
            (OrderState.OrderSent, ("processing", None)),
            (OrderState.OrderCreated, ("processing", None)),
        ],
    )
    def test_mapping(self, state, expected):
        assert sqs.status_for_order_state(state) == expected


class TestSyncToDuckDB:
    def _queue(self, dconn, qid, status="pending"):
        dconn.execute(
            "INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, price, status)"
            " VALUES (?, ?, '1234', 'buy', 100, 'limit', 1000, ?)",
            [qid, SIGNAL_DATE, status],
        )

    def test_sync_updates_non_pending_rows_only(self, sconn, dconn):
        for qid in ("q-filled", "q-failed", "q-pending", "q-untracked"):
            self._queue(dconn, qid)
        _rec(sconn, "q-filled", "filled")
        _rec(sconn, "q-failed", "failed", reason="insufficient cash")
        _rec(sconn, "q-pending", "pending")

        n = sqs.sync_to_duckdb(dconn, sconn)

        assert n == 2
        rows = {
            r[0]: (r[1], r[2] is not None)
            for r in dconn.execute(
                "SELECT signal_id, status, processed_at FROM signal_queue"
            ).fetchall()
        }
        assert rows["q-filled"] == ("filled", True)
        assert rows["q-failed"] == ("failed", True)
        assert rows["q-pending"] == ("pending", False)
        assert rows["q-untracked"] == ("pending", False)

    def test_sync_is_idempotent(self, sconn, dconn):
        self._queue(dconn, "q1")
        _rec(sconn, "q1", "cancelled", reason="duplicate")
        assert sqs.sync_to_duckdb(dconn, sconn) == 1
        assert sqs.sync_to_duckdb(dconn, sconn) == 0

    def test_sync_without_sqlite_table_is_noop(self, dconn):
        c = sqlite3.connect(":memory:")
        self._queue(dconn, "q1")
        assert sqs.sync_to_duckdb(dconn, c) == 0
