# tests/test_risk_manager.py
"""RiskManager 単体テスト"""
import sqlite3
import pytest
from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return OrderRepository(conn)


def _make_manager(broker, repo) -> RiskManager:
    config = RiskConfig(initial_portfolio_value=10_000_000.0)
    return RiskManager(broker=broker, repo=repo, config=config)


class TestGate1CheckSignal:

    def test_passes_when_all_checks_ok(self, repo):
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert result.passed

    def test_fails_when_insufficient_cash(self, repo):
        broker = MockBrokerClient(available_cash=50_000.0)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert not result.passed
        assert "余力" in result.reason

    def test_fails_when_duplicate_active_order(self, repo):
        broker = MockBrokerClient(available_cash=5_000_000.0)
        from kabusys.execution.order_record import OrderRecord
        from datetime import datetime, timezone
        active = OrderRecord(
            client_order_id="test-dup",
            signal_id="2026-03-29_1234_buy",
            code="1234", side="buy", qty=100,
            order_type="market", price=0.0,
            state=OrderState.OrderAccepted,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(active)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert not result.passed
        assert "重複" in result.reason

    def test_fails_when_position_limit_exceeded(self, repo):
        # 総資産 10,000,000 円、max_position_pct=0.10 → 1銘柄上限 1,000,000 円
        # 既存ポジション: 1234 @ current_price=2000, qty=400 → 800,000 円
        # 追加注文: 300,000 円 → 合計 1,100,000 円 > 1,000,000 円 → NG
        existing_pos = Position(code="1234", qty=400, avg_price=1800.0, current_price=2000.0)
        broker = MockBrokerClient(
            available_cash=5_000_000.0,
            initial_positions=[existing_pos],
        )
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=300_000.0)
        assert not result.passed
        assert "ポジション上限" in result.reason

    def test_fails_when_utilization_limit_exceeded(self, repo):
        # 総資産 10,000,000 円、max_utilization=0.80 → 全ポジション上限 8,000,000 円
        # 既存ポジション評価額: 7,800,000 円 (current_price あり)
        # 追加注文: 300,000 円 → 合計 8,100,000 円 > 8,000,000 円 → NG
        big_pos = Position(code="9999", qty=780, avg_price=9000.0, current_price=10000.0)
        broker = MockBrokerClient(
            available_cash=5_000_000.0,
            initial_positions=[big_pos],
        )
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=300_000.0)
        assert not result.passed
        assert "全体上限" in result.reason
