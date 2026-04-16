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


def test_start_clears_existing_stop_flag(tmp_path):
    flag = tmp_path / "stop.flag"
    flag.touch()

    with patch("start_system.STOP_FLAG_PATH", flag), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen") as mock_popen, \
         patch("start_system.write_pid"):
        mock_popen.return_value.pid = 1234
        _run_start()

    assert not flag.exists()


def test_start_already_running_exits_1(tmp_path):
    pid_path = tmp_path / "exec.pid"
    pid_path.write_text("1234")

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", pid_path), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=True):
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

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen", side_effect=fake_popen), \
         patch("start_system.write_pid"):
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

    with patch("start_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("start_system.EXECUTION_PID_PATH", tmp_path / "exec.pid"), \
         patch("start_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("start_system.is_process_running", return_value=False), \
         patch("start_system.subprocess.Popen", side_effect=fake_popen), \
         patch("start_system.write_pid"):
        _run_start()  # default = all

    assert len(launched) == 2
