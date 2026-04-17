# scripts/start_system.py
"""システム起動スクリプト。execution / monitoring プロセスを起動する。

使い方:
    python scripts/start_system.py                      # 両方起動
    python scripts/start_system.py --component execution
    python scripts/start_system.py --component monitoring
    python scripts/start_system.py --component all      # 両方（明示的）

    # 停止フラグが残っている場合に明示的にクリアして起動する
    python scripts/start_system.py --clear-stop-flag
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
    get_process_create_time,
    is_process_running,
    read_pid,
    write_pid,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
_MODULE_EXECUTION = "kabusys.run_execution"
_MODULE_MONITORING = "kabusys.run_monitoring"


def _launch(module: str, pid_path: Path) -> bool:
    """モジュールを -m オプションで subprocess 起動し、PID をファイルに書き込む。

    ファイルパス直指定ではなく ``python -m <module>`` で起動することで、
    sys.path[0] が src/ に設定され kabusys パッケージの import が正常に通る。

    Returns:
        True: 起動した。False: 既に起動中だったためスキップした。
    """
    existing_pid = read_pid(pid_path)
    if existing_pid is not None and is_process_running(existing_pid):
        logger.info(
            "既に起動中です (PID=%d, module=%s)。起動をスキップします。",
            existing_pid,
            module,
        )
        return False

    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        cwd=str(_SRC_DIR),
    )
    create_time = get_process_create_time(proc.pid)
    write_pid(pid_path, proc.pid, create_time)
    logger.info("%s を起動しました (PID=%d)", module, proc.pid)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys システム起動")
    parser.add_argument(
        "--component",
        choices=["execution", "monitoring", "all"],
        default="all",
        help="起動するコンポーネント (デフォルト: all)",
    )
    parser.add_argument(
        "--clear-stop-flag",
        action="store_true",
        help="停止フラグが残っている場合に明示的にクリアして起動する（Kill Switch 発動後の復旧用）",
    )
    args = parser.parse_args()

    # 停止フラグの確認
    if STOP_FLAG_PATH.exists():
        if args.clear_stop_flag:
            logger.info("--clear-stop-flag が指定されたため停止フラグをクリアします。")
            clear_stop_flag(STOP_FLAG_PATH)
        else:
            logger.error(
                "停止フラグが存在します (%s)。"
                "意図的に再起動する場合は --clear-stop-flag を指定してください。",
                STOP_FLAG_PATH,
            )
            sys.exit(1)

    launched = 0
    if args.component in ("execution", "all"):
        if _launch(_MODULE_EXECUTION, EXECUTION_PID_PATH):
            launched += 1

    if args.component in ("monitoring", "all"):
        if _launch(_MODULE_MONITORING, MONITORING_PID_PATH):
            launched += 1

    if launched == 0:
        logger.warning("起動対象のコンポーネントがすべて既に起動中です。")
        sys.exit(1)

    logger.info("起動完了 (component=%s, launched=%d)", args.component, launched)


if __name__ == "__main__":
    main()
