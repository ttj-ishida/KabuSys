# tests/test_broker_factory.py
import pytest

from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.mock_client import MockBrokerClient


class TestPaperFillMode:
    def test_default_is_instant(self, monkeypatch):
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        assert Settings().paper_fill_mode == "instant"

    def test_partial(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "partial")
        assert Settings().paper_fill_mode == "partial"

    def test_never(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "never")
        assert Settings().paper_fill_mode == "never"

    def test_reject(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "reject")
        assert Settings().paper_fill_mode == "reject"

    def test_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "bad_value")
        with pytest.raises(ValueError):
            Settings().paper_fill_mode

    def test_strip_and_lower(self, monkeypatch):
        monkeypatch.setenv("PAPER_FILL_MODE", "  PARTial  ")
        assert Settings().paper_fill_mode == "partial"


class TestPaperSqlitePath:
    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("PAPER_TRADING_SQLITE_PATH", raising=False)
        from pathlib import Path

        assert (
            Settings().paper_sqlite_path == Path("data/paper_trading.db").expanduser()
        )

    def test_override(self, monkeypatch, tmp_path):
        custom = str(tmp_path / "custom.db")
        monkeypatch.setenv("PAPER_TRADING_SQLITE_PATH", custom)
        assert str(Settings().paper_sqlite_path) == custom


class TestBrokerClientFactory:
    def test_paper_mode_returns_mock(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)

    def test_dev_mode_returns_mock(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "development")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)

    def test_fill_mode_applied(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("PAPER_FILL_MODE", "partial")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)
        assert broker.fill_mode == "partial"

    def test_fill_mode_default_instant(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert broker.fill_mode == "instant"

    def test_live_mode_returns_kabu_station_client(self, monkeypatch):
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "live")
        monkeypatch.setenv("KABU_API_PASSWORD", "test_password")
        monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        broker.close()  # httpx.Client を閉じる

    def test_live_mode_passes_trade_password_when_set(self, monkeypatch):
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "live")
        monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
        monkeypatch.setenv("KABU_TRADE_PASSWORD", "trade_pass")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        assert broker._trade_password == "trade_pass"
        broker.close()

    def test_live_mode_falls_back_to_api_password_when_trade_password_not_set(
        self, monkeypatch
    ):
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "live")
        monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
        monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        assert broker._trade_password == "api_pass"
        broker.close()

    def test_fill_mode_never_applied(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("PAPER_FILL_MODE", "never")
        broker = BrokerClientFactory.create(Settings())
        assert broker.fill_mode == "never"

    def test_fill_mode_reject_applied(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("PAPER_FILL_MODE", "reject")
        broker = BrokerClientFactory.create(Settings())
        assert broker.fill_mode == "reject"

    def test_unknown_env_raises_at_settings_level(self, monkeypatch):
        # 無効な KABUSYS_ENV は is_paper/is_dev/is_live の評価を経て
        # Factory 内の settings.env 明示評価で ValueError を投げる
        monkeypatch.setenv("KABUSYS_ENV", "unknown_env")
        with pytest.raises(ValueError):
            BrokerClientFactory.create(Settings())


class TestPaperTradingInitialCash:
    def test_default_is_ten_million(self, monkeypatch):
        monkeypatch.delenv("PAPER_TRADING_INITIAL_CASH", raising=False)
        assert Settings().paper_trading_initial_cash == 10_000_000.0

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("PAPER_TRADING_INITIAL_CASH", "5000000")
        assert Settings().paper_trading_initial_cash == 5_000_000.0

    def test_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("PAPER_TRADING_INITIAL_CASH", "not_a_number")
        with pytest.raises(ValueError):
            Settings().paper_trading_initial_cash

    def test_zero_raises(self, monkeypatch):
        monkeypatch.setenv("PAPER_TRADING_INITIAL_CASH", "0")
        with pytest.raises(ValueError):
            Settings().paper_trading_initial_cash

    def test_negative_raises(self, monkeypatch):
        monkeypatch.setenv("PAPER_TRADING_INITIAL_CASH", "-1000000")
        with pytest.raises(ValueError):
            Settings().paper_trading_initial_cash


class TestKabuSandbox:
    def test_sandbox_default_false(self, monkeypatch):
        monkeypatch.delenv("KABU_USE_SANDBOX", raising=False)
        assert Settings().kabu_use_sandbox is False

    def test_sandbox_enabled(self, monkeypatch):
        monkeypatch.setenv("KABU_USE_SANDBOX", "true")
        assert Settings().kabu_use_sandbox is True

    def test_sandbox_password_default_empty(self, monkeypatch):
        monkeypatch.delenv("KABU_SANDBOX_API_PASSWORD", raising=False)
        assert Settings().kabu_sandbox_api_password == ""

    def test_sandbox_password_set(self, monkeypatch):
        monkeypatch.setenv("KABU_SANDBOX_API_PASSWORD", "sandbox_pass")
        assert Settings().kabu_sandbox_api_password == "sandbox_pass"


class TestBrokerClientFactoryInitialCash:
    def test_initial_cash_applied_from_settings(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("PAPER_TRADING_INITIAL_CASH", "3000000")
        monkeypatch.delenv("KABU_USE_SANDBOX", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, MockBrokerClient)
        assert broker.get_available_cash() == 3_000_000.0

    def test_available_cash_override(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("KABU_USE_SANDBOX", raising=False)
        broker = BrokerClientFactory.create(Settings(), available_cash=999_000.0)
        assert isinstance(broker, MockBrokerClient)
        assert broker.get_available_cash() == 999_000.0

    def test_initial_positions_override(self, monkeypatch):
        from kabusys.execution.broker_api import Position

        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.delenv("KABU_USE_SANDBOX", raising=False)
        pos = Position(code="1234", qty=100, avg_price=1500.0)
        broker = BrokerClientFactory.create(Settings(), initial_positions=[pos])
        assert isinstance(broker, MockBrokerClient)
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].code == "1234"

    def test_sandbox_mode_returns_kabu_client(self, monkeypatch):
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("KABU_USE_SANDBOX", "true")
        monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
        monkeypatch.setenv("KABU_SANDBOX_API_PASSWORD", "sandbox_pass")
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        broker.close()

    def test_sandbox_falls_back_to_api_password(self, monkeypatch):
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("KABU_USE_SANDBOX", "true")
        monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
        monkeypatch.delenv("KABU_SANDBOX_API_PASSWORD", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        broker.close()

    def test_sandbox_uses_port_18081(self, monkeypatch):
        from kabusys.execution.broker_factory import _SANDBOX_BASE_URL
        from kabusys.execution.kabu_client import KabuStationClient

        monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
        monkeypatch.setenv("KABU_USE_SANDBOX", "true")
        monkeypatch.setenv("KABU_API_PASSWORD", "api_pass")
        monkeypatch.delenv("KABU_SANDBOX_API_PASSWORD", raising=False)
        broker = BrokerClientFactory.create(Settings())
        assert isinstance(broker, KabuStationClient)
        assert "18081" in _SANDBOX_BASE_URL
        broker.close()


class TestKabuTradePassword:
    def test_returns_none_when_not_set(self, monkeypatch):
        monkeypatch.delenv("KABU_TRADE_PASSWORD", raising=False)
        assert Settings().kabu_trade_password is None

    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("KABU_TRADE_PASSWORD", "secret123")
        assert Settings().kabu_trade_password == "secret123"

    def test_returns_none_for_empty_string(self, monkeypatch):
        monkeypatch.setenv("KABU_TRADE_PASSWORD", "")
        assert Settings().kabu_trade_password is None
