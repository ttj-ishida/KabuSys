"""MonitoringDB 単体テスト（Issue #36）"""

from datetime import datetime, timedelta, timezone

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def mdb(monitoring_conn):
    return MonitoringDB(monitoring_conn)


class TestInitMonitoringDb:
    def test_tables_created_idempotently(self, monitoring_conn):
        """init_monitoring_db を2回呼んでもエラーなし、6テーブルが存在する"""
        init_monitoring_db(monitoring_conn)  # 2回目の呼び出し
        tables = {
            row[0]
            for row in monitoring_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "system_status",
            "trade_logs",
            "positions",
            "risk_logs",
            "dashboard",
        }.issubset(tables)


class TestLogSystemStatus:
    def test_appends_row(self, mdb, monitoring_conn):
        """2回呼ぶと2行追記される"""
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        mdb.log_system_status(55.0, 65.0, 75.0, False)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM system_status"
        ).fetchone()[0]
        assert count == 2

    def test_default_recorded_at_is_utc_now(self, mdb, monitoring_conn):
        """`recorded_at` 省略時に ISO8601 UTC 文字列が入り、now との差が5秒以内"""
        before = datetime.now(timezone.utc)
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        after = datetime.now(timezone.utc)
        row = monitoring_conn.execute(
            "SELECT recorded_at FROM system_status"
        ).fetchone()
        recorded = datetime.fromisoformat(row[0])
        assert before - timedelta(seconds=5) <= recorded <= after + timedelta(seconds=5)


class TestLogTradeEvent:
    def test_appends_row_with_correct_fields(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_trade_event(
            event_type="filled",
            client_order_id="order-001",
            code="1234",
            side="buy",
            qty=100,
            price=1500.0,
            filled_qty=100,
            state="filled",
            logged_at=ts,
        )
        row = monitoring_conn.execute(
            "SELECT * FROM trade_logs WHERE client_order_id = 'order-001'"
        ).fetchone()
        assert row["event_type"] == "filled"
        assert row["code"] == "1234"
        assert row["qty"] == 100
        assert row["price"] == 1500.0
        assert row["filled_qty"] == 100
        assert row["state"] == "filled"

    def test_market_order_price_defaults_to_zero(self, mdb, monitoring_conn):
        """成行注文は price=0.0 で記録できる（order_repository.py と同規約）"""
        mdb.log_trade_event(
            event_type="order_created",
            client_order_id="order-002",
            code="5678",
            side="buy",
            qty=100,
            price=0.0,
            state="created",
        )
        row = monitoring_conn.execute(
            "SELECT price FROM trade_logs WHERE client_order_id = 'order-002'"
        ).fetchone()
        assert row[0] == 0.0

    def test_latency_ms_stored_and_retrieved(self, mdb, monitoring_conn):
        """latency_ms が正しく格納・取得できる"""
        mdb.log_trade_event(
            event_type="Sent",
            client_order_id="order-lat",
            code="1234",
            side="buy",
            qty=100,
            price=1500.0,
            state="sent",
            latency_ms=42.5,
        )
        row = monitoring_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE client_order_id = 'order-lat'"
        ).fetchone()
        assert row["latency_ms"] == pytest.approx(42.5)

    def test_latency_ms_defaults_to_none(self, mdb, monitoring_conn):
        """latency_ms 省略時は NULL が格納される"""
        mdb.log_trade_event(
            event_type="Created",
            client_order_id="order-nolat",
            code="5678",
            side="buy",
            qty=50,
            price=1000.0,
            state="created",
        )
        row = monitoring_conn.execute(
            "SELECT latency_ms FROM trade_logs WHERE client_order_id = 'order-nolat'"
        ).fetchone()
        assert row["latency_ms"] is None

    def test_migration_adds_latency_ms_column(self):
        """init_monitoring_db() が latency_ms カラムを trade_logs に追加する"""
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(":memory:")
        init_monitoring_db(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_logs)")}
        assert "latency_ms" in cols
        conn.close()

    def test_migration_is_idempotent(self):
        """init_monitoring_db() を2回呼んでも latency_ms カラムが1つだけ"""
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(":memory:")
        init_monitoring_db(conn)
        init_monitoring_db(conn)  # 2回目
        count = sum(
            1
            for row in conn.execute("PRAGMA table_info(trade_logs)")
            if row[1] == "latency_ms"
        )
        assert count == 1
        conn.close()


class TestUpsertPosition:
    def test_insert_new_position(self, mdb, monitoring_conn):
        """新規 code が挿入される"""
        mdb.upsert_position("1234", 100, 1500.0)
        count = monitoring_conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        assert count == 1

    def test_update_existing_position(self, mdb, monitoring_conn):
        """同一 code を2回 upsert すると上書きされる（行数は1のまま）"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.upsert_position("1234", 50, 1600.0)
        count = monitoring_conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        assert count == 1
        row = monitoring_conn.execute(
            "SELECT qty, avg_price FROM positions WHERE code = '1234'"
        ).fetchone()
        assert row[0] == 50
        assert row[1] == 1600.0

    def test_delete_position(self, mdb, monitoring_conn):
        """`delete_position` 後にその code は取得されない"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.delete_position("1234")
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions WHERE code = '1234'"
        ).fetchone()[0]
        assert count == 0


class TestLogRiskEvent:
    def test_appends_row(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_risk_event(
            event_type="drawdown_warning",
            metric_name="drawdown_pct",
            metric_value=5.5,
            threshold=5.0,
            detail='{"portfolio_value": 9450000}',
            logged_at=ts,
        )
        row = monitoring_conn.execute("SELECT * FROM risk_logs").fetchone()
        assert row["event_type"] == "drawdown_warning"
        assert row["metric_name"] == "drawdown_pct"
        assert row["metric_value"] == 5.5
        assert row["threshold"] == 5.0
        assert row["detail"] == '{"portfolio_value": 9450000}'

    def test_detail_can_be_none(self, mdb, monitoring_conn):
        """`detail` は NULL 可"""
        mdb.log_risk_event("circuit_breaker", "api_error_count", 3.0, 3.0)
        row = monitoring_conn.execute("SELECT detail FROM risk_logs").fetchone()
        assert row[0] is None


class TestUpsertDashboard:
    def test_first_upsert_creates_row(self, mdb, monitoring_conn):
        """最初の upsert でレコードが作成される"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        count = monitoring_conn.execute("SELECT COUNT(*) FROM dashboard").fetchone()[0]
        assert count == 1

    def test_second_upsert_overwrites(self, mdb, monitoring_conn):
        """2回 upsert しても行数は1のまま、値は最新"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        mdb.upsert_dashboard(9_500_000.0, 4_500_000.0, 5.0, 1, 3)
        count = monitoring_conn.execute("SELECT COUNT(*) FROM dashboard").fetchone()[0]
        assert count == 1

    def test_get_dashboard_returns_latest(self, mdb):
        """`get_dashboard()` が最新の dict を返す"""
        mdb.upsert_dashboard(10_000_000.0, 5_000_000.0, 0.0, 3, 5)
        mdb.upsert_dashboard(9_500_000.0, 4_500_000.0, 5.0, 1, 3)
        result = mdb.get_dashboard()
        assert result is not None
        assert result["portfolio_value"] == 9_500_000.0
        assert result["drawdown_pct"] == 5.0
        assert result["position_count"] == 3

    def test_get_dashboard_returns_none_when_empty(self, mdb):
        """レコードなし時は None を返す"""
        result = mdb.get_dashboard()
        assert result is None


class TestWizardMessages:
    def test_save_and_load_messages(self, mdb, monitoring_conn):
        """save → load でメッセージが挿入順に返る。"""
        mdb.save_wizard_message("sess1", "user", "テスト質問")
        mdb.save_wizard_message("sess1", "assistant", "テスト回答")
        msgs = mdb.load_wizard_messages("sess1")
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "テスト質問"}
        assert msgs[1] == {"role": "assistant", "content": "テスト回答"}

    def test_load_order_is_stable_within_same_second(self, mdb):
        """同一秒内に挿入された複数メッセージが挿入順（id 順）で返る。"""
        for i in range(5):
            mdb.save_wizard_message("sess_order", "user", f"msg{i}")
        msgs = mdb.load_wizard_messages("sess_order")
        assert [m["content"] for m in msgs] == [f"msg{i}" for i in range(5)]

    def test_load_empty_session(self, mdb):
        """存在しない session_id は空リストを返す。"""
        assert mdb.load_wizard_messages("nonexistent") == []

    def test_clear_removes_only_target_session(self, monitoring_conn):
        """clear は対象 session_id のみ削除し、別セッションは残る。"""
        db = MonitoringDB(monitoring_conn)
        db.save_wizard_message("sess1", "user", "question")
        db.save_wizard_message("sess2", "user", "other")
        db.clear_wizard_messages("sess1")
        assert db.load_wizard_messages("sess1") == []
        assert len(db.load_wizard_messages("sess2")) == 1

    def test_ai_wizard_messages_table_exists(self, monitoring_conn):
        """init_monitoring_db 後に ai_wizard_messages テーブルが存在する。"""
        tables = {
            row[0]
            for row in monitoring_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "ai_wizard_messages" in tables
