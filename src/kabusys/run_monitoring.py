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

import duckdb

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.monitoring.system_monitor import SystemMonitor
from kabusys.utils.process_priority import set_process_priority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 60  # 秒


def _get_poll_interval() -> int:
    """MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得する（デフォルト: 60秒）。"""
    try:
        return int(os.environ.get("MONITOR_POLL_INTERVAL", _DEFAULT_POLL_INTERVAL))
    except ValueError:
        logger.warning(
            "MONITOR_POLL_INTERVAL の値が不正です。デフォルト %d 秒を使用します。",
            _DEFAULT_POLL_INTERVAL,
        )
        return _DEFAULT_POLL_INTERVAL


def main() -> None:
    # 1. プロセス優先度を High に設定（最初に実行）
    set_process_priority("high")

    settings = Settings()
    logger.info("起動環境: KABUSYS_ENV=%s", settings.env)

    # 2. DB 接続（monitoring は環境にかかわらず本番 sqlite_path を使用）
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    init_monitoring_db(sqlite_conn)
    duckdb_conn = duckdb.connect(str(settings.duckdb_path))

    # 3. SystemMonitor 初期化
    monitor = SystemMonitor(
        conn=sqlite_conn,
        duckdb_conn=duckdb_conn,
        pid_file=settings.pid_file_path,
    )

    # 4. ポーリングループ
    poll_interval = _get_poll_interval()
    logger.info("監視ループ開始（ポーリング間隔: %d 秒）", poll_interval)
    try:
        while True:
            monitor.check_once()
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("監視ループを終了します。")


if __name__ == "__main__":
    main()
