# scripts/utils.py
"""PIDファイル・停止フラグ・プロセス生存確認の共通ユーティリティ。

すべての scripts/*.py から import して使う。
run_execution.py / run_monitoring.py は直接 _STOP_FLAG パスを使うため
このモジュールを import しない（PYTHONPATH 問題を避けるため）。
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import psutil
except ImportError:
    print(
        "ERROR: psutil がインストールされていません。"
        "pip install psutil を実行してください。",
        file=sys.stderr,
    )
    sys.exit(1)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXECUTION_PID_PATH = _PROJECT_ROOT / "data" / "execution.pid"
MONITORING_PID_PATH = _PROJECT_ROOT / "data" / "monitoring.pid"
STOP_FLAG_PATH = _PROJECT_ROOT / "data" / "stop_requested.flag"


def read_pid(path: Path) -> int | None:
    """PID ファイルを読み込む。ファイルが存在しないか不正な場合は None を返す。"""
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_pid(path: Path, pid: int) -> None:
    """PID をファイルに書き込む。親ディレクトリが存在しない場合は作成する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid))


def delete_pid(path: Path) -> None:
    """PID ファイルを削除する。存在しない場合は何もしない。"""
    path.unlink(missing_ok=True)


def is_process_running(pid: int) -> bool:
    """指定された PID のプロセスが生存しているかを返す。"""
    return psutil.pid_exists(pid)


def request_stop(flag_path: Path = STOP_FLAG_PATH) -> None:
    """停止フラグファイルを作成する。親ディレクトリが存在しない場合は作成する。"""
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.touch()


def stop_requested(flag_path: Path = STOP_FLAG_PATH) -> bool:
    """停止フラグファイルが存在するかを返す。"""
    return flag_path.exists()


def clear_stop_flag(flag_path: Path = STOP_FLAG_PATH) -> None:
    """停止フラグファイルを削除する。存在しない場合は何もしない。"""
    flag_path.unlink(missing_ok=True)
