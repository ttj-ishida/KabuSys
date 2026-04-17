# tests/test_start_system.py
"""scripts/start_system.py の単体テスト"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run_start(args: list[str] | None = None):
    """start_system.main() をモックで実行する。sys.argv をオーバーライド。"""
    import start_system

    with patch.object(sys, "argv", ["start_system.py"] + (args or [])):
        return start_system.main()


def test_start_stop_flag_without_clear_flag_exits_1(tmp_path):
    """停止フラグが存在し --clear-stop-flag を指定しない場合はエラー終了する。"""
    flag = tmp_path / "stop.flag"
    flag.touch()

    with (
        patch("start_system.STOP_FLAG_PATH", flag),
        patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
    ):
        with pytest.raises(SystemExit) as exc:
            _run_start()
        assert exc.value.code == 1

    # フラグは削除されていないこと
    assert flag.exists()


def test_start_clear_stop_flag_clears_and_starts(tmp_path):
    """--clear-stop-flag を指定すると停止フラグをクリアして起動する。"""
    flag = tmp_path / "stop.flag"
    flag.touch()

    with (
        patch("start_system.STOP_FLAG_PATH", flag),
        patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
        patch("start_system.is_process_running", return_value=False),
        patch("start_system.subprocess.Popen") as mock_popen,
        patch("start_system.write_pid"),
    ):
        mock_popen.return_value.pid = 1234
        _run_start(["--clear-stop-flag"])

    assert not flag.exists()


def test_start_already_running_exits_1(tmp_path):
    pid_path = tmp_path / "exec.pid"
    pid_path.write_text("1234")

    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system.EXECUTION_PID_PATH", pid_path),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
        patch("start_system.is_process_running", return_value=True),
    ):
        with pytest.raises(SystemExit) as exc:
            _run_start(["--component", "execution"])
        assert exc.value.code == 1


def test_start_component_execution_only(tmp_path):
    launched = []

    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        m = MagicMock()
        m.pid = 9999
        return m

    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
        patch("start_system.is_process_running", return_value=False),
        patch("start_system.subprocess.Popen", side_effect=fake_popen),
        patch("start_system.write_pid"),
    ):
        _run_start(["--component", "execution"])

    assert len(launched) == 1
    assert "kabusys.run_execution" in str(launched[0])


def test_start_all_launches_both(tmp_path):
    launched = []

    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        m = MagicMock()
        m.pid = 9999
        return m

    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
        patch("start_system.is_process_running", return_value=False),
        patch("start_system.subprocess.Popen", side_effect=fake_popen),
        patch("start_system.write_pid"),
    ):
        _run_start()  # default = all

    assert len(launched) == 2


# ---------------------------------------------------------------------------
# --dry-run モード
# ---------------------------------------------------------------------------


def test_dry_run_does_not_launch_process(tmp_path):
    """--dry-run 指定時にプロセスが起動しないこと。"""
    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"),
        patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"),
        patch("start_system._DRY_RUN_DEPS_AVAILABLE", False),
        patch("start_system.subprocess.Popen") as mock_popen,
    ):
        _run_start(["--dry-run"])

    mock_popen.assert_not_called()


def test_dry_run_reports_stop_flag_present(tmp_path, caplog):
    """--dry-run で停止フラグが存在する場合に「あり」とログ出力されること。"""
    import logging

    flag = tmp_path / "stop.flag"
    flag.touch()

    with (
        patch("start_system.STOP_FLAG_PATH", flag),
        patch("start_system._DRY_RUN_DEPS_AVAILABLE", False),
        caplog.at_level(logging.INFO, logger="start_system"),
    ):
        _run_start(["--dry-run"])

    assert "あり" in caplog.text


def test_dry_run_reports_stop_flag_absent(tmp_path, caplog):
    """--dry-run で停止フラグが存在しない場合に「なし」とログ出力されること。"""
    import logging

    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system._DRY_RUN_DEPS_AVAILABLE", False),
        caplog.at_level(logging.INFO, logger="start_system"),
    ):
        _run_start(["--dry-run"])

    assert "なし" in caplog.text


def test_dry_run_queries_duckdb(tmp_path, caplog):
    """--dry-run で DuckDB が利用可能なとき pending/processing/positions をログ出力すること。"""
    import logging

    duckdb_path = tmp_path / "kabusys.duckdb"
    duckdb_path.write_bytes(b"fake")

    settings_mock = MagicMock()
    settings_mock.duckdb_path = duckdb_path

    def fake_execute(sql, *args, **kwargs):
        m = MagicMock()
        m.fetchone.return_value = (3,)
        return m

    conn_mock = MagicMock()
    conn_mock.execute.side_effect = fake_execute

    with (
        patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"),
        patch("start_system._DRY_RUN_DEPS_AVAILABLE", True),
        patch("start_system._Settings", return_value=settings_mock),
        patch("start_system._duckdb.connect", return_value=conn_mock),
        caplog.at_level(logging.INFO, logger="start_system"),
    ):
        _run_start(["--dry-run"])

    assert "pending" in caplog.text
    assert "processing" in caplog.text
    assert "positions" in caplog.text
    conn_mock.close.assert_called_once()


def test_dry_run_does_not_clear_stop_flag(tmp_path):
    """--dry-run 指定時に停止フラグを削除しないこと。"""
    flag = tmp_path / "stop.flag"
    flag.touch()

    with (
        patch("start_system.STOP_FLAG_PATH", flag),
        patch("start_system._DRY_RUN_DEPS_AVAILABLE", False),
    ):
        _run_start(["--dry-run"])

    assert flag.exists()  # フラグは残ったまま
