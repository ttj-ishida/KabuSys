"""
audit モジュールのユニットテスト

テスト方針:
  - インメモリ DuckDB を使用し外部依存なし
  - init_audit_schema / init_audit_db の冪等性を確認
  - 各テーブルの制約（CHECK / FOREIGN KEY / UNIQUE）を検証
  - UUID 連鎖によるトレーサビリティ（signal → order → execution）を確認
  - ステータス遷移・棄却シグナルの永続化も検証
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import duckdb
import pytest
from duckdb import ConstraintException

from kabusys.data.audit import init_audit_schema, init_audit_db


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def audit_conn():
    """監査テーブル初期化済みのインメモリ DuckDB 接続。"""
    conn = duckdb.connect(":memory:")
    init_audit_schema(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _insert_signal(conn, **kwargs) -> str:
    sid = kwargs.get("signal_id", _uid())
    conn.execute(
        """
        INSERT INTO signal_events
            (signal_id, business_date, strategy_id, code, side, final_score, decision)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            sid,
            kwargs.get("business_date", "2025-01-06"),
            kwargs.get("strategy_id", "v1"),
            kwargs.get("code", "7203"),
            kwargs.get("side", "buy"),
            kwargs.get("final_score", 0.8),
            kwargs.get("decision", "buy"),
        ],
    )
    return sid


def _insert_order(conn, signal_id: str, **kwargs) -> str:
    oid = kwargs.get("order_request_id", _uid())
    conn.execute(
        """
        INSERT INTO order_requests
            (order_request_id, signal_id, business_date, code, side,
             requested_qty, order_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            oid,
            signal_id,
            kwargs.get("business_date", "2025-01-06"),
            kwargs.get("code", "7203"),
            kwargs.get("side", "buy"),
            kwargs.get("requested_qty", 100),
            kwargs.get("order_type", "market"),
            kwargs.get("status", "pending"),
        ],
    )
    return oid


def _insert_execution(conn, order_request_id: str, **kwargs) -> str:
    eid = kwargs.get("execution_id", _uid())
    conn.execute(
        """
        INSERT INTO executions
            (execution_id, order_request_id, broker_order_id,
             broker_execution_id, code, side, filled_qty, fill_price, executed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            eid,
            order_request_id,
            kwargs.get("broker_order_id", "B-001"),
            kwargs.get("broker_execution_id", _uid()),
            kwargs.get("code", "7203"),
            kwargs.get("side", "buy"),
            kwargs.get("filled_qty", 100),
            kwargs.get("fill_price", 2500.0),
            kwargs.get("executed_at", datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)),
        ],
    )
    return eid


# ---------------------------------------------------------------------------
# init_audit_schema / init_audit_db
# ---------------------------------------------------------------------------

class TestInitAuditSchema:
    def test_tables_created(self, audit_conn):
        tables = {
            row[0]
            for row in audit_conn.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        assert "signal_events" in tables
        assert "order_requests" in tables
        assert "executions" in tables

    def test_idempotent(self, audit_conn):
        """2 回呼んでもエラーにならない。"""
        init_audit_schema(audit_conn)
        init_audit_schema(audit_conn)

    def test_indexes_created(self, audit_conn):
        indexes = {
            row[0]
            for row in audit_conn.execute(
                "SELECT index_name FROM duckdb_indexes()"
            ).fetchall()
        }
        assert "idx_signal_events_date_code" in indexes
        assert "idx_order_requests_status" in indexes
        assert "idx_executions_order_request_id" in indexes

    def test_init_audit_db_memory(self):
        conn = init_audit_db(":memory:")
        assert conn is not None
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'signal_events'"
        ).fetchone()
        assert row[0] == 1
        conn.close()


# ---------------------------------------------------------------------------
# signal_events テーブル
# ---------------------------------------------------------------------------

class TestSignalEvents:
    def test_insert_buy_signal(self, audit_conn):
        sid = _insert_signal(audit_conn, decision="buy")
        row = audit_conn.execute(
            "SELECT signal_id, decision FROM signal_events WHERE signal_id = ?", [sid]
        ).fetchone()
        assert row[0] == sid
        assert row[1] == "buy"

    def test_rejected_by_risk_persisted(self, audit_conn):
        """リスク管理で棄却されたシグナルも永続化される。"""
        sid = _insert_signal(audit_conn, decision="rejected_by_risk")
        row = audit_conn.execute(
            "SELECT decision FROM signal_events WHERE signal_id = ?", [sid]
        ).fetchone()
        assert row[0] == "rejected_by_risk"

    def test_all_decision_values_valid(self, audit_conn):
        valid_decisions = [
            "buy", "sell", "hold",
            "rejected_by_risk", "rejected_by_position_limit",
            "rejected_by_drawdown", "cancelled", "error",
        ]
        for decision in valid_decisions:
            _insert_signal(audit_conn, decision=decision)

    def test_invalid_decision_raises(self, audit_conn):
        with pytest.raises(ConstraintException):
            _insert_signal(audit_conn, decision="unknown_decision")

    def test_invalid_side_raises(self, audit_conn):
        with pytest.raises(ConstraintException):
            _insert_signal(audit_conn, side="long")

    def test_primary_key_unique(self, audit_conn):
        sid = _uid()
        _insert_signal(audit_conn, signal_id=sid)
        with pytest.raises(ConstraintException):
            _insert_signal(audit_conn, signal_id=sid)

    def test_created_at_auto_set(self, audit_conn):
        sid = _insert_signal(audit_conn)
        row = audit_conn.execute(
            "SELECT created_at FROM signal_events WHERE signal_id = ?", [sid]
        ).fetchone()
        assert row[0] is not None

    def test_final_score_nullable(self, audit_conn):
        """final_score は NULL 許容（シグナル棄却時などスコア未計算の場合）。"""
        sid = _uid()
        audit_conn.execute(
            """
            INSERT INTO signal_events
                (signal_id, business_date, strategy_id, code, side, decision)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [sid, "2025-01-06", "v1", "7203", "buy", "buy"],
        )
        row = audit_conn.execute(
            "SELECT final_score FROM signal_events WHERE signal_id = ?", [sid]
        ).fetchone()
        assert row[0] is None


# ---------------------------------------------------------------------------
# order_requests テーブル
# ---------------------------------------------------------------------------

class TestOrderRequests:
    def test_insert_pending_order(self, audit_conn):
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        row = audit_conn.execute(
            "SELECT status FROM order_requests WHERE order_request_id = ?", [oid]
        ).fetchone()
        assert row[0] == "pending"

    def test_idempotent_key_unique(self, audit_conn):
        """同一 order_request_id で 2 度 INSERT すると例外。"""
        sid = _insert_signal(audit_conn)
        oid = _uid()
        _insert_order(audit_conn, sid, order_request_id=oid)
        with pytest.raises(ConstraintException):
            _insert_order(audit_conn, sid, order_request_id=oid)

    def test_foreign_key_signal_id(self, audit_conn):
        """存在しない signal_id は FK エラー。"""
        with pytest.raises(ConstraintException):
            _insert_order(audit_conn, "nonexistent-signal-id")

    def test_all_status_values_valid(self, audit_conn):
        for status in ["pending", "sent", "filled", "partially_filled",
                       "cancelled", "rejected", "error"]:
            sid = _insert_signal(audit_conn)
            _insert_order(audit_conn, sid, status=status)

    def test_invalid_status_raises(self, audit_conn):
        sid = _insert_signal(audit_conn)
        with pytest.raises(ConstraintException):
            _insert_order(audit_conn, sid, status="unknown")

    def test_limit_order_requires_limit_price(self, audit_conn):
        """limit 注文: limit_price が必須。"""
        sid = _insert_signal(audit_conn)
        with pytest.raises(ConstraintException):
            audit_conn.execute(
                """
                INSERT INTO order_requests
                    (order_request_id, signal_id, business_date, code, side,
                     requested_qty, order_type)
                VALUES (?, ?, ?, ?, ?, ?, 'limit')
                """,
                [_uid(), sid, "2025-01-06", "7203", "buy", 100],
            )

    def test_market_order_no_prices(self, audit_conn):
        """market 注文: limit_price / stop_price は不要（NULL のまま OK）。"""
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid, order_type="market")
        row = audit_conn.execute(
            "SELECT limit_price, stop_price FROM order_requests WHERE order_request_id = ?",
            [oid],
        ).fetchone()
        assert row[0] is None
        assert row[1] is None

    def test_status_update(self, audit_conn):
        """pending → sent へのステータス更新。"""
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        audit_conn.execute(
            "UPDATE order_requests SET status = 'sent' WHERE order_request_id = ?", [oid]
        )
        row = audit_conn.execute(
            "SELECT status FROM order_requests WHERE order_request_id = ?", [oid]
        ).fetchone()
        assert row[0] == "sent"

    def test_broker_order_id_unique_index(self, audit_conn):
        """broker_order_id に UNIQUE インデックスが効いている。"""
        sid = _insert_signal(audit_conn)
        oid1 = _insert_order(audit_conn, sid)
        oid2 = _uid()
        # 同一 broker_order_id を別 order_request に設定しようとすると失敗
        broker_id = "B-DUP-001"
        audit_conn.execute(
            "UPDATE order_requests SET broker_order_id = ? WHERE order_request_id = ?",
            [broker_id, oid1],
        )
        _insert_order(audit_conn, sid, order_request_id=oid2)
        with pytest.raises(ConstraintException):
            audit_conn.execute(
                "UPDATE order_requests SET broker_order_id = ? WHERE order_request_id = ?",
                [broker_id, oid2],
            )


# ---------------------------------------------------------------------------
# executions テーブル
# ---------------------------------------------------------------------------

class TestExecutions:
    def test_insert_execution(self, audit_conn):
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        eid = _insert_execution(audit_conn, oid)
        row = audit_conn.execute(
            "SELECT filled_qty, fill_price FROM executions WHERE execution_id = ?",
            [eid],
        ).fetchone()
        assert row[0] == 100
        assert float(row[1]) == 2500.0

    def test_broker_execution_id_unique(self, audit_conn):
        """broker_execution_id は UNIQUE（冪等キー）。"""
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        beid = _uid()
        _insert_execution(audit_conn, oid, broker_execution_id=beid)
        with pytest.raises(ConstraintException):
            _insert_execution(audit_conn, oid, broker_execution_id=beid)

    def test_foreign_key_order_request_id(self, audit_conn):
        """存在しない order_request_id は FK エラー。"""
        with pytest.raises(ConstraintException):
            _insert_execution(audit_conn, "nonexistent-order-id")

    def test_filled_qty_positive(self, audit_conn):
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        with pytest.raises(ConstraintException):
            _insert_execution(audit_conn, oid, filled_qty=0)

    def test_fill_price_non_negative(self, audit_conn):
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        with pytest.raises(ConstraintException):
            _insert_execution(audit_conn, oid, fill_price=-1.0)

    def test_commission_default_zero(self, audit_conn):
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid)
        eid = _insert_execution(audit_conn, oid)
        row = audit_conn.execute(
            "SELECT commission FROM executions WHERE execution_id = ?", [eid]
        ).fetchone()
        assert float(row[0]) == 0.0


# ---------------------------------------------------------------------------
# UUID 連鎖トレーサビリティ
# ---------------------------------------------------------------------------

class TestUUIDChainTraceability:
    def test_full_chain_signal_to_execution(self, audit_conn):
        """signal → order → execution の UUID 連鎖が結合できる。"""
        sid = _insert_signal(audit_conn, code="7203", decision="buy")
        oid = _insert_order(audit_conn, sid, code="7203")
        eid = _insert_execution(audit_conn, oid, code="7203")

        # signal_id を起点に execution まで辿れる
        row = audit_conn.execute(
            """
            SELECT e.execution_id, e.fill_price
            FROM executions e
            JOIN order_requests o ON e.order_request_id = o.order_request_id
            JOIN signal_events s  ON o.signal_id = s.signal_id
            WHERE s.signal_id = ?
            """,
            [sid],
        ).fetchone()
        assert row is not None
        assert row[0] == eid

    def test_one_signal_multiple_orders(self, audit_conn):
        """1 つのシグナルから複数の発注（分割発注等）が可能。"""
        sid = _insert_signal(audit_conn)
        oid1 = _insert_order(audit_conn, sid, requested_qty=50)
        oid2 = _insert_order(audit_conn, sid, requested_qty=50)
        rows = audit_conn.execute(
            "SELECT order_request_id FROM order_requests WHERE signal_id = ?", [sid]
        ).fetchall()
        assert len(rows) == 2
        assert {r[0] for r in rows} == {oid1, oid2}

    def test_one_order_multiple_executions(self, audit_conn):
        """1 つの発注から複数の約定（部分約定等）が可能。"""
        sid = _insert_signal(audit_conn)
        oid = _insert_order(audit_conn, sid, requested_qty=100)
        eid1 = _insert_execution(audit_conn, oid, filled_qty=60, broker_execution_id=_uid())
        eid2 = _insert_execution(audit_conn, oid, filled_qty=40, broker_execution_id=_uid())
        rows = audit_conn.execute(
            "SELECT execution_id FROM executions WHERE order_request_id = ?", [oid]
        ).fetchall()
        assert len(rows) == 2
        assert {r[0] for r in rows} == {eid1, eid2}

    def test_rejected_signal_has_no_order(self, audit_conn):
        """棄却シグナルには order_requests が存在しないことを確認。"""
        sid = _insert_signal(audit_conn, decision="rejected_by_risk")
        rows = audit_conn.execute(
            "SELECT * FROM order_requests WHERE signal_id = ?", [sid]
        ).fetchall()
        assert rows == []

    def test_business_date_consistent_across_chain(self, audit_conn):
        """business_date が signal → order で一致している。"""
        bdate = "2025-03-14"
        sid = _insert_signal(audit_conn, business_date=bdate)
        oid = _insert_order(audit_conn, sid, business_date=bdate)
        row = audit_conn.execute(
            """
            SELECT s.business_date, o.business_date
            FROM signal_events s
            JOIN order_requests o ON s.signal_id = o.signal_id
            WHERE s.signal_id = ?
            """,
            [sid],
        ).fetchone()
        assert str(row[0]) == bdate
        assert str(row[1]) == bdate
