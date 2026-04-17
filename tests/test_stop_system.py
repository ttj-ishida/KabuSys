# tests/test_stop_system.py
"""scripts/stop_system.py の単体テスト"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _run_stop(tmp_path, exec_pid=None, mon_pid=None, process_alive=True, exits_within_timeout=True,
              exec_create_time=None, mon_create_time=None):
    """stop_system.main() をモックで実行するヘルパー。"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    mon_pid_path = tmp_path / "mon.pid"
    flag_path = tmp_path / "stop.flag"

    if exec_pid:
        content = str(exec_pid) if exec_create_time is None else f"{exec_pid}\n{exec_create_time}"
        exec_pid_path.write_text(content)
    if mon_pid:
        content = str(mon_pid) if mon_create_time is None else f"{mon_pid}\n{mon_create_time}"
        mon_pid_path.write_text(content)

    # is_process_running: initially True (process running), then:
    # - exits_within_timeout=True: returns False after a few calls (graceful exit)
    # - exits_within_timeout=False: always returns True (force kill needed)
    if process_alive:
        if exits_within_timeout:
            # True for initial check in main(), then True a few more times in loop, then False
            running_side_effects = [True, True, True, False] + [False] * 20
        else:
            running_side_effects = [True] * 40
    else:
        running_side_effects = [False] * 40

    mock_psutil = MagicMock()
    mock_proc = MagicMock()
    mock_psutil.Process.return_value = mock_proc
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", mon_pid_path), \
         patch("stop_system.STOP_FLAG_PATH", flag_path), \
         patch("stop_system.is_process_running", side_effect=running_side_effects), \
         patch("stop_system.get_process_create_time", return_value=None), \
         patch("stop_system.psutil", mock_psutil), \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        stop_system.main()

    return flag_path, exec_pid_path, mon_pid_path, mock_proc, mock_psutil


def test_stop_creates_flag(tmp_path):
    flag, _, _, _, _ = _run_stop(tmp_path, exec_pid=1234, process_alive=False)
    assert flag.exists()  # flag は stop_system.py が残す（start_system.py がクリア）


def test_stop_graceful_no_kill(tmp_path):
    _, _, _, mock_proc, mock_psutil = _run_stop(
        tmp_path, exec_pid=1234, exits_within_timeout=True
    )
    mock_psutil.Process.return_value.kill.assert_not_called()


def test_stop_force_kill_on_timeout(tmp_path):
    _, _, _, mock_proc, mock_psutil = _run_stop(
        tmp_path, exec_pid=1234, exits_within_timeout=False
    )
    mock_psutil.Process.return_value.kill.assert_called()


def test_stop_missing_pid_file_is_skipped(tmp_path):
    # exec PIDなし、mon PIDなし → エラーにならない
    flag, exec_pid, mon_pid, _, _ = _run_stop(tmp_path)
    assert not exec_pid.exists()
    assert not mon_pid.exists()


def test_stop_deletes_pid_files_after_exit(tmp_path):
    _, exec_pid, mon_pid, _, _ = _run_stop(
        tmp_path, exec_pid=1234, mon_pid=5678, exits_within_timeout=True
    )
    assert not exec_pid.exists()
    assert not mon_pid.exists()


def test_stop_partial_failure_handles_both(tmp_path):
    """execution がグレースフル終了、monitoring がタイムアウト → kill が1回呼ばれる"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    mon_pid_path = tmp_path / "mon.pid"
    flag_path = tmp_path / "stop.flag"
    exec_pid_path.write_text("1234")
    mon_pid_path.write_text("5678")

    mock_psutil = MagicMock()
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
    exec_proc = MagicMock()
    mon_proc = MagicMock()

    def make_proc(pid):
        return exec_proc if pid == 1234 else mon_proc

    mock_psutil.Process.side_effect = make_proc

    # execution: alive (True), then exits (False) after a few checks
    # monitoring: always alive (True) - timeout → kill
    call_count = [0]

    def is_running_side_effect(pid):
        call_count[0] += 1
        if pid == 1234:
            # Returns True for first check in main(), then False in _wait_or_kill loop
            return call_count[0] <= 2
        else:
            # monitoring never exits
            return True

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", mon_pid_path), \
         patch("stop_system.STOP_FLAG_PATH", flag_path), \
         patch("stop_system.is_process_running", side_effect=is_running_side_effect), \
         patch("stop_system.get_process_create_time", return_value=None), \
         patch("stop_system.psutil", mock_psutil), \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        stop_system.main()

    exec_proc.kill.assert_not_called()
    mon_proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# create_time 照合テスト
# ---------------------------------------------------------------------------

def test_stop_skips_kill_on_create_time_mismatch(tmp_path):
    """PID ファイルの create_time と実際のプロセスが異なる場合はスキップする。"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    exec_pid_path.write_text("1234\n1000.0")  # stored create_time = 1000.0

    mock_psutil = MagicMock()
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("stop_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("stop_system.is_process_running", return_value=True), \
         patch("stop_system.get_process_create_time", return_value=9999.0), \
         patch("stop_system.psutil", mock_psutil), \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        stop_system.main()

    # create_time 不一致 → kill されていないこと
    mock_psutil.Process.return_value.kill.assert_not_called()
    # PID ファイルは削除されること
    assert not exec_pid_path.exists()


def test_stop_kills_when_create_time_matches(tmp_path):
    """create_time が一致する場合は通常通り kill する。"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    exec_pid_path.write_text("1234\n1000.0")  # stored create_time = 1000.0

    mock_psutil = MagicMock()
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("stop_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("stop_system.is_process_running", return_value=True), \
         patch("stop_system.get_process_create_time", return_value=1000.0), \
         patch("stop_system.psutil", mock_psutil), \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        stop_system.main()

    mock_psutil.Process.return_value.kill.assert_called()


def test_stop_no_create_time_in_pid_file_proceeds_normally(tmp_path):
    """旧形式（create_time なし）の PID ファイルでも照合をスキップして正常動作する。"""
    import stop_system

    exec_pid_path = tmp_path / "exec.pid"
    exec_pid_path.write_text("1234")  # 旧形式: PID のみ

    mock_psutil = MagicMock()
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

    with patch("stop_system.EXECUTION_PID_PATH", exec_pid_path), \
         patch("stop_system.MONITORING_PID_PATH", tmp_path / "mon.pid"), \
         patch("stop_system.STOP_FLAG_PATH", tmp_path / "stop.flag"), \
         patch("stop_system.is_process_running", return_value=True), \
         patch("stop_system.get_process_create_time", return_value=1000.0), \
         patch("stop_system.psutil", mock_psutil), \
         patch("stop_system.time.sleep"), \
         patch("stop_system.time.monotonic", side_effect=list(range(60))):
        stop_system.main()

    # create_time 未記録 → 照合スキップ → 通常通り kill
    mock_psutil.Process.return_value.kill.assert_called()
