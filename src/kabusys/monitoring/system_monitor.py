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
        if today is None:
            today = date.today()

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        # Windows 対応: "/" は無効。Path.cwd().drive（例: "C:\\"）を使用。
        # 空の場合（Linux/テスト）は "/" にフォールバック。
        disk_path = Path.cwd().drive + "\\" if Path.cwd().drive else "/"
        disk = psutil.disk_usage(disk_path).percent

        process_ok, stale_pid_detected = self._check_process()
        data_freshness_ok = self._check_data_freshness(today)

        now_utc = datetime.now(timezone.utc)
        self._db.log_system_status(
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            recorded_at=now_utc,
        )

        return SystemCheckResult(
            recorded_at=now_utc.isoformat(),
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            process_ok=process_ok,
            data_freshness_ok=data_freshness_ok,
            stale_pid_detected=stale_pid_detected,
        )

    def _check_process(self) -> tuple[bool, bool]:
        """PID ファイルを確認してプロセス生存を判定する。

        Returns:
            (process_ok, stale_pid_detected)
        """
        if not self._pid_file.exists():
            return False, False

        try:
            pid = int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            self._pid_file.unlink(missing_ok=True)
            return False, True

        if psutil.pid_exists(pid):
            return True, False

        # Stale PID: プロセス死亡 → ファイル削除
        self._pid_file.unlink(missing_ok=True)
        return False, True

    def _check_data_freshness(self, today: date) -> bool:
        """DuckDB の最終株価更新日が十分新しいか確認する。

        Returns:
            True if (today - last_price_date).days <= DATA_STALE_DAYS
        """
        last = pipeline.get_last_price_date(self._duckdb_conn)
        if last is None:
            return False
        return (today - last).days <= DATA_STALE_DAYS
