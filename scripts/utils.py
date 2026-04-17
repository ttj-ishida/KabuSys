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
    """PID ファイルを読み込む（後方互換）。不正な場合は None を返す。"""
    entry = read_pid_entry(path)
    return entry[0] if entry is not None else None


def read_pid_entry(path: Path) -> tuple[int, float | None] | None:
    """PID と起動時刻を読み込む。

    ファイル形式:
        新形式: 1行目=PID, 2行目=create_time (float)
        旧形式: 1行目=PID のみ（create_time は None）

    ファイルが存在しないか不正な場合は None を返す。
    """
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        pid = int(lines[0])
        create_time = float(lines[1]) if len(lines) >= 2 else None
        return (pid, create_time)
    except (OSError, ValueError, IndexError):
        return None


def write_pid(path: Path, pid: int, create_time: float | None = None) -> None:
    """PID（と起動時刻）をファイルに書き込む。親ディレクトリが存在しない場合は作成する。

    create_time を渡すと新形式（PID\\nCREATE_TIME）で書き込む。
    省略した場合は旧形式（PID のみ）で書き込む。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = str(pid) if create_time is None else f"{pid}\n{create_time}"
    path.write_text(content, encoding="utf-8")


def get_process_create_time(pid: int) -> float | None:
    """プロセスの起動時刻（Unix タイムスタンプ）を返す。取得できない場合は None。"""
    try:
        return psutil.Process(pid).create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


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
