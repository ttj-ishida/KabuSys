
import os
from unittest import mock

import pytest

from kabusys import run_monitoring


def test_get_poll_interval_default(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert run_monitoring._get_poll_interval() == 60


@pytest.mark.parametrize("val, expected", [
    ("30", 30),
    ("1", 1),
])
def test_get_poll_interval_valid(monkeypatch, val, expected):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", val)
    assert run_monitoring._get_poll_interval() == expected


@pytest.mark.parametrize("badval", ["0", "-5", "abc", "", "  "])
def test_get_poll_interval_invalid(monkeypatch, badval, caplog):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", badval)
    caplog.clear()
    val = run_monitoring._get_poll_interval()
    assert val == 60
    assert any("MONITOR_POLL_INTERVAL" in rec.message for rec in caplog.records)


def test_main_exits_when_stop_flag_exists(monkeypatch):
    # Patch process priority
    mp = mock.MagicMock()
    monkeypatch.setattr(run_monitoring, "set_process_priority", mp)

    # Fake Settings
    fake_settings = mock.MagicMock()
    fake_settings.env = "development"
    fake_settings.sqlite_path = "/tmp/nonexistent.sqlite"
    fake_settings.duckdb_path = "/tmp/nonexistent.duckdb"
    fake_settings.pid_file_path = "/tmp/pid"
    monkeypatch.setattr(run_monitoring, "Settings", lambda: fake_settings)

    # Patch sqlite3 and duckdb connections
    fake_sqlite = mock.MagicMock()
    fake_duck = mock.MagicMock()
    monkeypatch.setattr("sqlite3.connect", lambda path: fake_sqlite)
    monkeypatch.setattr(run_monitoring, "duckdb", mock.MagicMock(connect=lambda p: fake_duck))

    # init_monitoring_db no-op
    monkeypatch.setattr(run_monitoring, "init_monitoring_db", lambda conn: None)

    # Ensure stop flag causes immediate exit
    monkeypatch.setattr(run_monitoring._STOP_FLAG, "exists", lambda: True)

    # Run main, should not raise and should close connections
    run_monitoring.main()

    fake_sqlite.close.assert_called_once()
    fake_duck.close.assert_called_once()
    mp.assert_called_once_with("high")
