
import os
import importlib
import logging

import pytest

# ensure config auto-load is disabled for tests
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"

from kabusys.run_monitoring import _get_poll_interval

def test_get_poll_interval_default(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == 60

def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "5")
    assert _get_poll_interval() == 5

def test_get_poll_interval_zero_or_negative(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == 60
    assert "不正" in caplog.text or "デフォルト" in caplog.text

    caplog.clear()
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-10")
    assert _get_poll_interval() == 60
    assert caplog.text

def test_get_poll_interval_nonint(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "not-an-int")
    assert _get_poll_interval() == 60
    assert "不正" in caplog.text or "デフォルト" in caplog.text
