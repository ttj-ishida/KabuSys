"""Settings の手動運用設定のテスト"""

from __future__ import annotations

import pytest

from kabusys.config import Settings


def test_manual_trading_defaults(monkeypatch):
    monkeypatch.delenv("MANUAL_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("MANUAL_TRADING_INITIAL_CASH", raising=False)
    monkeypatch.setenv("PORTFOLIO_VALUE", "3000000")
    s = Settings()
    assert s.manual_trading_enabled is False
    assert s.manual_trading_initial_cash == 3_000_000.0


def test_manual_trading_initial_cash_explicit(monkeypatch):
    monkeypatch.setenv("MANUAL_TRADING_ENABLED", "true")
    monkeypatch.setenv("MANUAL_TRADING_INITIAL_CASH", "2000000")
    s = Settings()
    assert s.manual_trading_enabled is True
    assert s.manual_trading_initial_cash == 2_000_000.0


def test_manual_trading_initial_cash_invalid(monkeypatch):
    monkeypatch.setenv("MANUAL_TRADING_INITIAL_CASH", "abc")
    with pytest.raises(ValueError):
        _ = Settings().manual_trading_initial_cash
