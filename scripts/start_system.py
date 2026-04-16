# scripts/start_system.py
"""システム起動スクリプト。execution / monitoring プロセスを起動する。

使い方:
    python scripts/start_system.py                      # 両方起動
    python scripts/start_system.py --component execution
    python scripts/start_system.py --component monitoring
    python scripts/start_system.py --component all      # 両方（明示的）
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# scripts/ ディレクトリを sys.path に追加して utils をインポート
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    EXECUTION_PID_PATH,
    MONITORING_PID_PATH,
    STOP_FLAG_PATH,
    clear_stop_flag,
    is_process_running,
    read_pid,
    write_pid,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUN_EXECUTION = _PROJECT_ROOT / "src" / "kabusys" / "run_execution.py"
_RUN_MONITORING = _PROJECT_ROOT / "src" / "kabusys" / "run_monitoring.py"


def _launch(script: Path, pid_path: Path) -> None:
    """スクリプトを subprocess で起動し、PID をファイルに書き込む。"""
    existing_pid = read_pid(pid_path)
    if existing_pid is not None and is_process_running(existing_pid):
        logger.warning(
            "既に起動中です (PID=%d, script=%s)。起動をスキップします。",
            existing_pid,
            script.name,
        )
        sys.exit(1)

    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(_PROJECT_ROOT),
    )
    write_pid(pid_path, proc.pid)
    logger.info("%s を起動しました (PID=%d)", script.name, proc.pid)


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys システム起動")
    parser.add_argument(
        "--component",
        choices=["execution", "monitoring", "all"],
        default="all",
        help="起動するコンポーネント (デフォルト: all)",
    )
    args = parser.parse_args()

    # 停止フラグをクリア（前回停止時のフラグが残っている場合）
    clear_stop_flag(STOP_FLAG_PATH)

    if args.component in ("execution", "all"):
        _launch(_RUN_EXECUTION, EXECUTION_PID_PATH)

    if args.component in ("monitoring", "all"):
        _launch(_RUN_MONITORING, MONITORING_PID_PATH)

    logger.info("起動完了 (component=%s)", args.component)


if __name__ == "__main__":
    main()
