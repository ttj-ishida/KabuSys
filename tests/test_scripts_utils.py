# tests/test_scripts_utils.py
"""scripts/utils.py の単体テスト"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# scripts/ ディレクトリを PYTHONPATH に追加してインポート
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import utils as script_utils


def test_read_pid_missing_file(tmp_path):
    assert script_utils.read_pid(tmp_path / "missing.pid") is None


def test_read_pid_invalid_content(tmp_path):
    p = tmp_path / "bad.pid"
    p.write_text("not-an-int")
    assert script_utils.read_pid(p) is None


def test_write_and_read_pid_roundtrip(tmp_path):
    p = tmp_path / "test.pid"
    script_utils.write_pid(p, 12345)
    assert script_utils.read_pid(p) == 12345


def test_write_pid_creates_parent_dirs(tmp_path):
    p = tmp_path / "sub" / "dir" / "test.pid"
    script_utils.write_pid(p, 99)
    assert p.exists()


def test_delete_pid_removes_file(tmp_path):
    p = tmp_path / "test.pid"
    p.write_text("1")
    script_utils.delete_pid(p)
    assert not p.exists()


def test_delete_pid_missing_file_is_noop(tmp_path):
    script_utils.delete_pid(tmp_path / "nonexistent.pid")  # should not raise


def test_is_process_running_current_process():
    assert script_utils.is_process_running(os.getpid()) is True


def test_is_process_running_invalid_pid():
    assert script_utils.is_process_running(9_999_999) is False


def test_stop_flag_lifecycle(tmp_path):
    flag = tmp_path / "stop.flag"
    assert not script_utils.stop_requested(flag)
    script_utils.request_stop(flag)
    assert script_utils.stop_requested(flag)
    script_utils.clear_stop_flag(flag)
    assert not script_utils.stop_requested(flag)


def test_request_stop_creates_parent_dirs(tmp_path):
    flag = tmp_path / "sub" / "stop.flag"
    script_utils.request_stop(flag)
    assert flag.exists()
