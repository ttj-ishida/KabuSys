# src/kabusys/run_monitoring.py
"""run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。

MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する。
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path

import duckdb

from kabusys.config import Settings

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
_MONITORING_PID = Path(__file__).resolve().parents[2] / "data" / "monitoring.pid"
from kabusys.monitoring.monitoring_db import init_monitoring_db  # noqa: E402
from kabusys.monitoring.system_monitor import SystemMonitor  # noqa: E402
from kabusys.utils.logging_setup import setup_logging  # noqa: E402
from kabusys.utils.process_priority import set_process_priority  # noqa: E402

logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 60  # 秒


def _get_poll_interval() -> int:
    """MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得する（デフォルト: 60秒）。

    0 以下の値はデフォルトにフォールバックする（time.sleep に渡すと ValueError が発生するため）。
    """
    raw = os.environ.get("MONITOR_POLL_INTERVAL", str(_DEFAULT_POLL_INTERVAL))
    try:
        val = int(raw)
        if val < 1:
            raise ValueError("non-positive")
        return val
    except ValueError:
        logger.warning(
            "MONITOR_POLL_INTERVAL の値が不正です（%r）。デフォルト %d 秒を使用します。",
            raw,
            _DEFAULT_POLL_INTERVAL,
        )
        return _DEFAULT_POLL_INTERVAL


def main() -> None:
    setup_logging(app_name="monitoring")
    # 1. プロセス優先度を High に設定（最初に実行）
    set_process_priority("high")

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続（monitoring は環境にかかわらず本番 sqlite_path を使用）
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    init_monitoring_db(sqlite_conn)
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)

    # 3. SystemMonitor 初期化
    monitor = SystemMonitor(
        conn=sqlite_conn,
        duckdb_conn=duckdb_conn,
        pid_file=settings.pid_file_path,
    )

    # 4. ポーリングループ
    poll_interval = _get_poll_interval()
    logger.info("監視ループ開始（ポーリング間隔: %d 秒）", poll_interval)
    _MONITORING_PID.parent.mkdir(parents=True, exist_ok=True)
    _MONITORING_PID.write_text(str(os.getpid()))
    try:
        while True:
            if _STOP_FLAG.exists():
                logger.info("停止フラグを検知。監視ループを終了します。")
                break
            try:
                monitor.check_once()
            except Exception:
                logger.exception(
                    "check_once() で予期しないエラーが発生しました。次のポーリングまで待機します。"
                )
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("監視ループを終了します。")
    finally:
        sqlite_conn.close()
        duckdb_conn.close()
        _MONITORING_PID.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
