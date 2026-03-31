# src/kabusys/monitoring/system_monitor.py
"""SystemMonitor — CPU/メモリ/ディスク・プロセス生存・データ鮮度を1回チェックして記録するクラス。

ポーリング間隔の管理は呼び出し元が担当。内部ループは持たない。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import psutil
from duckdb import DuckDBPyConnection

from kabusys.data import pipeline
from kabusys.monitoring.monitoring_db import MonitoringDB

DATA_STALE_DAYS = 3  # 株価データが N 日以上古い場合を異常とする


@dataclass
class SystemCheckResult:
    recorded_at: str          # ISO8601 UTC
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_ok: bool          # プロセスが生存しているか
    data_freshness_ok: bool   # 株価データが十分新鮮か
    stale_pid_detected: bool  # stale PID を検出・削除した場合 True


class SystemMonitor:
    """システム状態・データ鮮度を1回チェックして MonitoringDB に記録するクラス。"""

    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
    ) -> None:
        self._db = MonitoringDB(conn)
        self._duckdb_conn = duckdb_conn
        self._pid_file = pid_file

    def check_once(self, today: date | None = None) -> SystemCheckResult:
        """1回分のシステム状態チェックを実行し、DB に記録して結果を返す。

        Args:
            today: データ鮮度判定の基準日（None → date.today()）。テスト時に注入。
        """
        raise NotImplementedError
