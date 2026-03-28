# tests/test_risk_manager.py
"""RiskManager 単体テスト"""
import sqlite3
import pytest
from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
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


class TestGate2CheckExecution:

    def test_passes_initially(self, repo):
        broker = MockBrokerClient()
        rm = _make_manager(broker, repo)
        result = rm.check_execution()
        assert result.passed

    def test_rate_limit_rejects_after_burst(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(rate_limit_per_sec=3, initial_portfolio_value=10_000_000.0)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        # 3回は通る
        for _ in range(3):
            r = rm.check_execution()
            assert r.passed
        # 4回目は reject
        r = rm.check_execution()
        assert not r.passed
        assert "レート制限" in r.reason

    def test_circuit_breaker_opens_after_n_errors(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=3,
            circuit_breaker_window_sec=60,
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        assert rm.check_execution().passed  # まだ CLOSED
        rm.record_api_error()
        result = rm.check_execution()
        assert not result.passed
        assert "サーキットブレーカー" in result.reason

    def test_circuit_breaker_half_open_after_window(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=2,
            circuit_breaker_window_sec=0,  # ウィンドウ = 0秒 → 即 HALF_OPEN
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        assert not rm.check_execution().passed  # OPEN
        # window=0 → 即 HALF_OPEN 遷移
        result = rm.check_execution()
        assert result.passed  # HALF_OPEN で1件許可

    def test_circuit_breaker_closes_on_success(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=2,
            circuit_breaker_window_sec=0,
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        rm.check_execution()        # OPEN → HALF_OPEN
        rm.check_execution()        # HALF_OPEN: 1件許可
        rm.record_api_success()     # CLOSED に遷移
        assert rm.check_execution().passed  # CLOSED で通過
