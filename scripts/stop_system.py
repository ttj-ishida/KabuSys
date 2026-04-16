# scripts/stop_system.py
"""システム停止スクリプト。

停止フラグファイルを作成し、execution / monitoring プロセスのグレースフル終了を待つ。
10秒以内に終了しない場合は強制終了する。
停止フラグは削除しない（次回 start_system.py 起動時にクリアされる）。
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    print("ERROR: psutil が必要です。pip install psutil を実行してください。", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    EXECUTION_PID_PATH,
    MONITORING_PID_PATH,
    STOP_FLAG_PATH,
    delete_pid,
    is_process_running,
    read_pid,
    request_stop,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_GRACEFUL_TIMEOUT_SEC = 10
_POLL_INTERVAL_SEC = 0.5


def _wait_or_kill(pid: int, label: str) -> None:
    """プロセスがグレースフルに終了するのを待ち、タイムアウト後に強制終了する。"""
    deadline = time.monotonic() + _GRACEFUL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if not is_process_running(pid):
            logger.info("%s (PID=%d) がグレースフルに終了しました。", label, pid)
            return
        time.sleep(_POLL_INTERVAL_SEC)
    logger.warning(
        "%s (PID=%d) がタイムアウト後も終了しません。強制終了します。", label, pid
    )
    try:
        psutil.Process(pid).kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.warning("強制終了できませんでした (PID=%d): %s", pid, e)


def main() -> None:
    logger.info("停止フラグを作成します: %s", STOP_FLAG_PATH)
    request_stop(STOP_FLAG_PATH)

    for pid_path, label in [
        (EXECUTION_PID_PATH, "execution_service"),
        (MONITORING_PID_PATH, "monitoring_service"),
    ]:
        pid = read_pid(pid_path)
        if pid is None:
            logger.info(
                "%s の PID ファイルが見つかりません。スキップします。"
                "（片方のコンポーネントのみ起動中の場合は正常）",
                label,
            )
            continue
        if not is_process_running(pid):
            logger.info("%s (PID=%d) は既に停止しています。", label, pid)
            delete_pid(pid_path)
            continue

        _wait_or_kill(pid, label)
        delete_pid(pid_path)

    logger.info(
        "停止処理完了。停止フラグ (%s) は次回起動時にクリアされます。", STOP_FLAG_PATH
    )


if __name__ == "__main__":
    main()
