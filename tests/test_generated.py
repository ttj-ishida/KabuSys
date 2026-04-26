
import os
import importlib
import logging

import pytest

from kabusys import run_monitoring


def test_get_poll_interval_default(monkeypatch):
    # 環境変数未設定時はデフォルト値
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert run_monitoring._get_poll_interval() == 60


def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "10")
    assert run_monitoring._get_poll_interval() == 10


def test_get_poll_interval_invalid_values(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert run_monitoring._get_poll_interval() == 60
    assert "値が不正" in "".join(caplog.messages) or caplog.records

    caplog.clear()
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-5")
    assert run_monitoring._get_poll_interval() == 60

    caplog.clear()
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "notanint")
    assert run_monitoring._get_poll_interval() == 60
