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

    def test_live_mode_raises_not_implemented(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_ENV", "live")
        with pytest.raises(NotImplementedError):
            BrokerClientFactory.create(Settings())

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
