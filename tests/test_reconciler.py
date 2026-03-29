"""Reconciler 単体テスト（Issue #32）"""
import sqlite3
import pytest
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.reconciler import Reconciler, ReconcileResult, PositionDiscrepancy


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return OrderRepository(conn)


def _make_reconciler(broker, repo) -> Reconciler:
    order_manager = OrderManager(broker=broker, repo=repo)
    return Reconciler(broker=broker, repo=repo, order_manager=order_manager)


class TestReconcilerNoOp:

    def test_returns_empty_result_when_no_uncertain_orders(self, repo):
        """uncertain 注文なし → ReconcileResult(0, 0, [])"""
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 0
        assert result.orders_no_status == 0
        assert result.position_discrepancies == []


class TestReconcileOrders:

    def test_broker_order_id_none_increments_no_status(self, repo):
        """broker_order_id=None の OrderSent は orders_no_status をインクリメント"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-001",
            signal_id="2026-03-29_1234_buy",
            code="1234", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        # broker_order_id は None のまま（デフォルト）
        repo.save(record)
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_no_status == 1
        assert result.orders_synced == 0
        # 状態は変化しない
        updated = repo.get("test-sent-001")
        assert updated.state == OrderState.OrderSent

    def test_broker_returns_open_transitions_to_accepted(self, repo):
        """broker → 'open' なら OrderAccepted に遷移し orders_synced=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-002",
            signal_id="2026-03-29_5678_buy",
            code="5678", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER002",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()
        broker._orders["BROKER002"] = OrderStatus(
            order_id="BROKER002", code="5678", side="buy",
            qty=100, filled_qty=0, status="open", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 1
        assert result.orders_no_status == 0
        assert repo.get("test-sent-002").state == OrderState.OrderAccepted

    def test_broker_returns_filled_transitions_to_filled(self, repo):
        """broker → 'filled' なら Filled に遷移し orders_synced=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-003",
            signal_id="2026-03-29_9012_buy",
            code="9012", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER003",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()
        broker._orders["BROKER003"] = OrderStatus(
            order_id="BROKER003", code="9012", side="buy",
            qty=100, filled_qty=100, status="filled", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 1
        assert repo.get("test-sent-003").state == OrderState.Filled

    def test_get_order_status_returns_none_increments_no_status(self, repo):
        """broker_order_id 設定済みだが get_order_status() が None → orders_no_status=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-004",
            signal_id="2026-03-29_3333_buy",
            code="3333", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER_MISSING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()  # _orders に "BROKER_MISSING" なし → None を返す
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_no_status == 1
        assert result.orders_synced == 0
        assert repo.get("test-sent-004").state == OrderState.OrderSent

    def test_sync_order_broker_api_error_skips_and_continues(self, repo):
        """sync_order が BrokerAPIError を raise → スキップして他の注文は続行"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus, BrokerAPIError
        from datetime import datetime, timezone
        # 2件の OrderSent を作成
        for i, cid in enumerate(["sent-err-001", "sent-ok-001"], start=1):
            r = OrderRecord(
                client_order_id=cid,
                signal_id=f"2026-03-29_{1000+i}_buy",
                code=str(1000 + i), side="buy", qty=100,
                order_type="limit", price=1500.0,
                state=OrderState.OrderSent,
                broker_order_id=f"BROKER_X{i}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            repo.save(r)
        broker = MockBrokerClient()
        broker._orders["BROKER_X2"] = OrderStatus(
            order_id="BROKER_X2", code="1002", side="buy",
            qty=100, filled_qty=0, status="open", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        # sent-err-001 の sync_order を BrokerAPIError にパッチ
        original_sync = reconciler._order_manager.sync_order
        def patched_sync(cid):
            if cid == "sent-err-001":
                raise BrokerAPIError("API failure")
            return original_sync(cid)
        reconciler._order_manager.sync_order = patched_sync
        result = reconciler.run()
        # sent-ok-001 は正常に処理される
        assert result.orders_synced == 1
        assert repo.get("sent-ok-001").state == OrderState.OrderAccepted

    def test_sync_order_unexpected_exception_skips_and_continues(self, repo):
        """sync_order が BrokerAPIError 以外の例外を raise → スキップして他の注文は続行"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from datetime import datetime, timezone
        for i, cid in enumerate(["sent-exc-001", "sent-exc-ok-001"], start=1):
            r = OrderRecord(
                client_order_id=cid,
                signal_id=f"2026-03-29_{2000+i}_buy",
                code=str(2000 + i), side="buy", qty=100,
                order_type="limit", price=1500.0,
                state=OrderState.OrderSent,
                broker_order_id=f"BROKER_E{i}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            repo.save(r)
        broker = MockBrokerClient()
        broker._orders["BROKER_E2"] = OrderStatus(
            order_id="BROKER_E2", code="2002", side="buy",
            qty=100, filled_qty=0, status="open", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        original_sync = reconciler._order_manager.sync_order
        def patched_sync(cid):
            if cid == "sent-exc-001":
                raise RuntimeError("unexpected DB error")
            return original_sync(cid)
        reconciler._order_manager.sync_order = patched_sync
        result = reconciler.run()
        # 例外は伝播しない
        assert result.orders_synced == 1
        assert repo.get("sent-exc-ok-001").state == OrderState.OrderAccepted

    def test_list_uncertain_exception_returns_empty_result(self, repo):
        """list_uncertain が Exception → ReconcileResult(0, 0, []) を返す、例外は伝播しない"""
        from unittest.mock import patch
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        with patch.object(repo, "list_uncertain", side_effect=Exception("DB error")):
            result = reconciler.run()
        assert result.orders_synced == 0
        assert result.orders_no_status == 0
        assert result.position_discrepancies == []


class TestReconcilePositions:

    def _insert_filled_order(
        self, repo, code: str, side: str, qty: int, cid: str
    ) -> None:
        """Filled 状態の注文を DB に直接挿入するヘルパー。"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id=cid,
            signal_id=f"sig_{cid}",
            code=code, side=side, qty=qty,
            order_type="limit", price=1500.0,
            state=OrderState.Filled,
            filled_qty=qty,
            broker_order_id=f"BRK_{cid}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)

    def test_no_discrepancy_when_positions_match(self, repo):
        """broker と local が一致 → position_discrepancies=[]"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-001")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=100, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.position_discrepancies == []

    def test_discrepancy_detected_when_broker_has_more(self, repo):
        """broker 100株、local 80株 → diff=+20 の PositionDiscrepancy"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 80, "pos-002")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=100, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert len(result.position_discrepancies) == 1
        d = result.position_discrepancies[0]
        assert d.code == "1234"
        assert d.broker_qty == 100
        assert d.local_qty == 80
        assert d.diff == 20

    def test_discrepancy_detected_when_local_has_more(self, repo):
        """local 100株、broker 0株 → diff=-100 の PositionDiscrepancy"""
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-003")
        broker = MockBrokerClient()  # ポジションなし
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert len(result.position_discrepancies) == 1
        assert result.position_discrepancies[0].diff == -100

    def test_net_position_accounts_for_sell_orders(self, repo):
        """buy 100株 - sell 30株 = local 70株; broker 70株 → 差分なし"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-buy-001")
        self._insert_filled_order(repo, "1234", "sell", 30, "pos-sell-001")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=70, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.position_discrepancies == []

    def test_get_positions_failure_skips_position_check(self, repo):
        """`get_positions()` が BrokerAPIError → position_discrepancies=[] で続行"""
        from unittest.mock import patch
        from kabusys.execution.broker_api import BrokerAPIError
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-004")
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        with patch.object(broker, "get_positions", side_effect=BrokerAPIError("API error")):
            result = reconciler.run()
        assert result.position_discrepancies == []
        # 処理は続行している（例外が伝播していない）

    def test_list_active_exception_skips_position_check(self, repo):
        """`list_active()` が Exception → position_discrepancies=[] で続行、例外は伝播しない"""
        from unittest.mock import patch
        from kabusys.execution.broker_api import Position
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=100, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        with patch.object(repo, "list_active", side_effect=Exception("DB error")):
            result = reconciler.run()
        assert result.position_discrepancies == []

    def test_broker_same_code_multiple_positions_are_summed(self, repo):
        """broker が同一コードで複数エントリを返した場合、合算される"""
        from unittest.mock import patch
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-005")
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        # MockBrokerClient は内部 dict でコードを上書きするため get_positions を直接モック
        multi_positions = [
            Position(code="1234", qty=60, avg_price=1500.0),
            Position(code="1234", qty=40, avg_price=1520.0),
        ]
        with patch.object(broker, "get_positions", return_value=multi_positions):
            result = reconciler.run()
        # broker 合計 100 == local 100 → 差分なし
        assert result.position_discrepancies == []


class TestExecutionEngineIntegration:

    def test_run_session_calls_reconciler_before_signal_processing(self, sqlite_conn, duckdb_conn):
        """reconciler.run() が run_session 内で WebSocket 起動より先に呼ばれる"""
        from datetime import date, time
        from unittest.mock import MagicMock
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
        from kabusys.execution.order_manager import OrderManager
        from kabusys.execution.risk_manager import RiskConfig, RiskManager
        from kabusys.execution.reconciler import Reconciler, ReconcileResult

        broker = MockBrokerClient(available_cash=5_000_000.0)
        repo = OrderRepository(sqlite_conn)
        risk_manager = RiskManager(broker=broker, repo=repo, config=RiskConfig(initial_portfolio_value=10_000_000.0))
        order_manager = OrderManager(broker=broker, repo=repo)
        reconciler = MagicMock(spec=Reconciler)
        reconciler.run.return_value = ReconcileResult()

        cfg = EngineConfig(
            target_date=date(2026, 3, 29),
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),   # シグナル処理をスキップ
            market_close=time(0, 0),       # 即終了
        )
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=cfg,
            reconciler=reconciler,
        )
        engine.run_session()
        reconciler.run.assert_called_once()

    def test_run_session_without_reconciler_does_not_raise(self, sqlite_conn, duckdb_conn):
        """reconciler=None（デフォルト）でも run_session は正常動作する"""
        from datetime import date, time
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
        from kabusys.execution.order_manager import OrderManager
        from kabusys.execution.risk_manager import RiskConfig, RiskManager

        broker = MockBrokerClient(available_cash=5_000_000.0)
        repo = OrderRepository(sqlite_conn)
        risk_manager = RiskManager(broker=broker, repo=repo, config=RiskConfig(initial_portfolio_value=10_000_000.0))
        order_manager = OrderManager(broker=broker, repo=repo)
        cfg = EngineConfig(
            target_date=date(2026, 3, 29),
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),
            market_close=time(0, 0),
        )
        # reconciler を渡さない（デフォルト None）→ 例外なし
        engine = ExecutionEngine(
            broker=broker, repo=repo, risk_manager=risk_manager,
            order_manager=order_manager, duckdb_conn=duckdb_conn, config=cfg,
        )
        engine.run_session()  # 例外が出なければ PASS
