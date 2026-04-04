# tests/test_broker_factory.py
import os
import pytest
from kabusys.config import Settings


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


class TestPaperSqlitePath:
    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("PAPER_TRADING_SQLITE_PATH", raising=False)
        path = Settings().paper_sqlite_path
        assert path.name == "paper_trading.db"
        assert "data" in str(path)

    def test_override(self, monkeypatch, tmp_path):
        custom = str(tmp_path / "custom.db")
        monkeypatch.setenv("PAPER_TRADING_SQLITE_PATH", custom)
        assert str(Settings().paper_sqlite_path) == custom
