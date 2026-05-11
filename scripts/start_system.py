# scripts/start_system.py
"""システム起動スクリプト。execution / monitoring プロセスを起動する。

使い方:
    python scripts/start_system.py                      # 両方起動
    python scripts/start_system.py --component execution
    python scripts/start_system.py --component monitoring
    python scripts/start_system.py --component all      # 両方（明示的）

    # 停止フラグが残っている場合に明示的にクリアして起動する
    python scripts/start_system.py --clear-stop-flag

    # 発注なしでリコンシリエーションと状態確認のみ実行（再開判断前の確認用）
    python scripts/start_system.py --dry-run
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
    import duckdb as _duckdb

    from kabusys.config import Settings as _Settings

    _DRY_RUN_DEPS_AVAILABLE = True
except ImportError:
    _DRY_RUN_DEPS_AVAILABLE = False

try:
    from kabusys.utils.logging_setup import setup_logging as _setup_logging

    _setup_logging(app_name="start_system")
except ImportError:
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


def _run_dry_run() -> None:
    """--dry-run モード: 発注なしで DB 状態を確認してログ出力する。"""
    prefix = "[DRY-RUN]"

    # 停止フラグ状態を報告
    flag_status = "あり" if STOP_FLAG_PATH.exists() else "なし"
    logger.info("%s 停止フラグ: %s (%s)", prefix, flag_status, STOP_FLAG_PATH)

    # DuckDB / Settings の依存がない場合はここで終了
    if not _DRY_RUN_DEPS_AVAILABLE:
        logger.warning(
            "%s duckdb または kabusys.config が利用不可のため DB 状態確認をスキップします。",
            prefix,
        )
        logger.info(
            "%s 発注は行いません。通常起動は --clear-stop-flag を指定してください。",
            prefix,
        )
        return

    try:
        settings = _Settings()
        if not settings.duckdb_path.exists():
            logger.warning(
                "%s DuckDB ファイルが見つかりません: %s", prefix, settings.duckdb_path
            )
            logger.info(
                "%s 発注は行いません。通常起動は --clear-stop-flag を指定してください。",
                prefix,
            )
            return

        conn = _duckdb.connect(str(settings.duckdb_path), read_only=True)
        try:
            # signal_queue の pending 件数
            pending = conn.execute(
                "SELECT COUNT(*) FROM signal_queue WHERE status = 'pending'"
            ).fetchone()[0]

            # 未処理 orders（sent 状態）件数（リコンシリエーション対象）
            sent_orders = conn.execute(
                "SELECT COUNT(*) FROM signal_queue WHERE status = 'processing'"
            ).fetchone()[0]

            # positions 件数
            positions = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]

        finally:
            conn.close()

        logger.info(
            "%s signal_queue: pending=%d 件, processing=%d 件（リコンシリエーション対象）",
            prefix,
            pending,
            sent_orders,
        )
        logger.info("%s positions: %d 件", prefix, positions)
        logger.info(
            "%s 発注は行いません。通常起動は --clear-stop-flag を指定してください。",
            prefix,
        )

    except Exception:
        logger.exception("%s DB 状態確認中にエラーが発生しました。", prefix)


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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="発注なしで DB 状態確認のみ実行（再開判断前の確認用）",
    )
    args = parser.parse_args()

    # --dry-run モード: プロセス起動なしで状態確認のみ
    if args.dry_run:
        _run_dry_run()
        return

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
