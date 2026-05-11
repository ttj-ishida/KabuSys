# tests/test_scripts_maintenance.py
"""reset_signals.py / rebuild_features.py の単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


# ---------- reset_signals ----------


def _run_reset_maintenance(mock_conn, tmp_path):
    """reset_signals.main() を --force 付きで実行するヘルパー。"""
    import reset_signals

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    with (
        patch.object(sys, "argv", ["reset_signals.py", "--force"]),
        patch("reset_signals._is_trading_hours", return_value=False),
        patch("reset_signals._count_open_orders", return_value=0),
        patch("reset_signals._backup_duckdb", return_value=tmp_path / "backup.duckdb"),
        patch("reset_signals.Settings") as mock_settings,
        patch("reset_signals.duckdb.connect", return_value=mock_conn),
    ):
        mock_settings.return_value.duckdb_path = duckdb_path
        mock_settings.return_value.sqlite_path = tmp_path / "monitoring.db"
        reset_signals.main()


def test_reset_signals_clears_rows(tmp_path):

    mock_conn = MagicMock()
    # information_schema: table exists (1), then DELETE
    mock_conn.execute.side_effect = [
        MagicMock(fetchone=lambda: (1,)),  # table exists check
        MagicMock(rowcount=3),  # DELETE
    ]

    _run_reset_maintenance(mock_conn, tmp_path)

    delete_calls = [c for c in mock_conn.execute.call_args_list if "DELETE" in str(c)]
    assert len(delete_calls) == 1


def test_reset_signals_empty_table_is_ok(tmp_path):

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = [
        MagicMock(fetchone=lambda: (1,)),  # table exists
        MagicMock(rowcount=0),  # DELETE 0件
    ]

    _run_reset_maintenance(mock_conn, tmp_path)  # SystemExit が起きないこと


# ---------- rebuild_features ----------


def test_rebuild_features_no_data_exits_1():
    import rebuild_features

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_conn.execute.return_value = mock_cursor

    with (
        patch("rebuild_features.Settings") as mock_settings,
        patch("rebuild_features.duckdb.connect", return_value=mock_conn),
        patch("rebuild_features.build_features") as mock_fn,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        with pytest.raises(SystemExit) as exc:
            rebuild_features.main()
        assert exc.value.code == 1

    mock_fn.assert_not_called()


def test_rebuild_features_with_data_calls_build_features():
    import rebuild_features

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (5,)
    mock_conn.execute.return_value = mock_cursor

    with (
        patch("rebuild_features.Settings") as mock_settings,
        patch("rebuild_features.duckdb.connect", return_value=mock_conn),
        patch("rebuild_features.build_features", return_value=5) as mock_fn,
    ):
        mock_settings.return_value.duckdb_path = Path("/fake.duckdb")
        rebuild_features.main()

    mock_fn.assert_called_once()
