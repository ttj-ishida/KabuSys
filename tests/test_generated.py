
import os
import logging

import pytest

from kabusys.run_monitoring import _get_poll_interval, _DEFAULT_POLL_INTERVAL


def test_get_poll_interval_default(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == _DEFAULT_POLL_INTERVAL


@pytest.mark.parametrize("val,expected", [
    ("30", 30),
    ("1", 1),
    ("  15  ", 15),
])
def test_get_poll_interval_valid(monkeypatch, val, expected):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", val)
    assert _get_poll_interval() == expected


@pytest.mark.parametrize("bad", ["0", "-5", "abc", "1.5", ""])
def test_get_poll_interval_invalid(monkeypatch, caplog, bad):
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", bad)
    val = _get_poll_interval()
    assert val == _DEFAULT_POLL_INTERVAL
    assert "MONITOR_POLL_INTERVAL" in caplog.text
