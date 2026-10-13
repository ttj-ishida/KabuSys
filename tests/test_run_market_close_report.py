# tests/test_run_market_close_report.py
"""run_market_close_report の SQLite 選択（Issue #413 fix round 1 / I4）。"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import kabusys.run_market_close_report as mod


def _settings(tmp_path: Path, *, is_paper: bool) -> MagicMock:
    s = MagicMock()
    s.is_paper = is_paper
    s.sqlite_path = tmp_path / "prod.db"
    s.paper_sqlite_path = tmp_path / "paper.db"
    s.duckdb_path = tmp_path / "data.duckdb"
    return s


def test_sqlite_path_follows_env_like_run_execution(tmp_path):
    assert mod._sqlite_path(_settings(tmp_path, is_paper=True)) == tmp_path / "paper.db"
    assert mod._sqlite_path(_settings(tmp_path, is_paper=False)) == tmp_path / "prod.db"


def test_open_sqlite_missing_file_uses_empty_db_without_creating(tmp_path):
    path = tmp_path / "missing.db"
    conn = mod._open_sqlite_readonly(path)
    try:
        assert conn.execute("SELECT 1").fetchone() == (1,)
    finally:
        conn.close()
    assert not path.exists()


def test_open_sqlite_existing_file_is_read_only(tmp_path):
    path = tmp_path / "x.db"
    sqlite3.connect(str(path)).close()
    conn = mod._open_sqlite_readonly(path)
    try:
        try:
            conn.execute("CREATE TABLE t (a INTEGER)")
            raise AssertionError("read-only のはず")
        except sqlite3.OperationalError:
            pass
    finally:
        conn.close()


def test_main_reads_paper_sqlite_in_paper_mode(tmp_path):
    settings = _settings(tmp_path, is_paper=True)
    with (
        patch("kabusys.run_market_close_report.Settings", return_value=settings),
        patch("kabusys.run_market_close_report.duckdb.connect"),
        patch("kabusys.run_market_close_report._open_sqlite_readonly") as mock_open,
        patch("kabusys.run_market_close_report.collect_market_close_data") as mock_collect,
        patch("kabusys.run_market_close_report.build_report") as mock_build,
        patch("kabusys.run_market_close_report.format_cli_summary", return_value=""),
    ):
        mock_build.return_value.status = "OK"
        mod.main(["--date", "2026-04-28"])

    mock_open.assert_called_once_with(tmp_path / "paper.db")
    assert mock_collect.call_args.args[2] == date(2026, 4, 28)
