"""system_monitor.py — システム状態・データ鮮度を監視する。"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

import duckdb
import psutil

from kabusys.data.pipeline import get_last_price_date
from kabusys.monitoring.monitoring_db import MonitoringDB

_FRESHNESS_DAYS = 3  # ≤3 日は許容（週末・祝日のギャップをカバー）


@dataclass(frozen=True)
class SystemCheckResult:
    recorded_at: str          # ISO8601 UTC
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    process_ok: bool
    data_freshness_ok: bool
    stale_pid_detected: bool


class SystemMonitor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        duckdb_conn: duckdb.DuckDBPyConnection,
        pid_file: Path = Path("data/execution.pid"),
        disk_path: str | None = None,
    ) -> None:
        self._db = MonitoringDB(conn)
        self._duckdb_conn = duckdb_conn
        self._pid_file = pid_file
        self._disk_path = disk_path or (str(Path.cwd().anchor) or "/")

    def check_once(self, today: date | None = None) -> SystemCheckResult:
        today = today or date.today()
        now = datetime.now(timezone.utc)
        recorded_at = now.isoformat()

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(self._disk_path).percent

        process_ok, stale_pid = self._check_process()
        data_ok = self._check_data_freshness(today)

        self._db.log_system_status(
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            recorded_at=now,
        )

        if stale_pid:
            self._db.log_risk_event(
                event_type="STALE_PID",
                metric_name="process",
                metric_value=0.0,
                threshold=1.0,
                detail="stale PID file detected and removed",
            )

        return SystemCheckResult(
            recorded_at=recorded_at,
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            data_freshness_ok=data_ok,
            stale_pid_detected=stale_pid,
        )

    def _check_process(self) -> tuple[bool, bool]:
        """(process_ok, stale_pid_detected) を返す。"""
        if not self._pid_file.exists():
            return False, False
        try:
            pid = int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            logger.warning("Invalid PID file %s — removing", self._pid_file)
            self._pid_file.unlink(missing_ok=True)
            return False, True
        if psutil.pid_exists(pid):
            return True, False
        # stale PID — 削除してアラート
        self._pid_file.unlink(missing_ok=True)
        return False, True

    def _check_data_freshness(self, today: date) -> bool:
        last = get_last_price_date(self._duckdb_conn)
        if last is None:
            return False
        return (today - last).days <= _FRESHNESS_DAYS
