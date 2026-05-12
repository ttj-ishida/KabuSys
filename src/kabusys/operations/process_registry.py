# src/kabusys/operations/process_registry.py
"""process_registry — バッチ・プロセスの実行状況を monitoring.db に記録するユーティリティ。

各バッチスクリプトは以下のパターンで使用する:

    from kabusys.operations.process_registry import register_process, update_process

    run_id = register_process("data_update_job", log_file="logs/data_update_...")
    try:
        ...
    finally:
        update_process(run_id, status="success")
"""

from __future__ import annotations

import errno
import logging
import os
import sqlite3

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

logger = logging.getLogger(__name__)


def is_pid_alive(pid: int) -> bool:
    """PID が生存しているかを返す。"""
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True
        except OSError as e:
            return getattr(e, "errno", None) == errno.EPERM


def register_process(job_name: str, log_file: str | None = None) -> int:
    """process_runs に開始レコードを挿入して run_id を返す。

    monitoring.db への書き込みに失敗した場合は例外を呼び出し元に伝播する。
    スクリプト側は try/except で受け取り、失敗時も main 処理を継続すること。

    Args:
        job_name: ジョブ識別子（例: ``"data_update_job"``）。
        log_file: 実行単位ログファイルのパス文字列（省略可）。

    Returns:
        run_id（process_runs テーブルの id）。
    """
    settings = Settings()
    conn = sqlite3.connect(str(settings.sqlite_path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        init_monitoring_db(conn)
        db = MonitoringDB(conn)
        db.prune_old_process_runs()
        return db.start_process(job_name=job_name, pid=os.getpid(), log_file=log_file)
    finally:
        conn.close()


def update_process(
    run_id: int,
    status: str,
    error_msg: str | None = None,
) -> None:
    """process_runs のレコードを完了・失敗として更新する。

    Args:
        run_id:    ``register_process`` が返した run_id。
        status:    ``"success"`` / ``"warning"`` / ``"failed"``。
        error_msg: 失敗時のエラーメッセージ（省略可）。
    """
    settings = Settings()
    conn = sqlite3.connect(str(settings.sqlite_path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        db = MonitoringDB(conn)
        cur = db.finish_process(run_id=run_id, status=status, error_msg=error_msg)
        if cur == 0:
            logger.warning("process_registry: run_id=%d が見つかりません", run_id)
    finally:
        conn.close()


def list_processes(hours: int = 24) -> list[dict]:
    """直近 hours 時間のプロセス一覧を返す（実行中含む）。

    Args:
        hours: 取得範囲（時間）。デフォルト 24 時間。

    Returns:
        process_runs レコードの dict リスト（started_at 降順）。
    """
    settings = Settings()
    conn = sqlite3.connect(str(settings.sqlite_path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        init_monitoring_db(conn)
        db = MonitoringDB(conn)
        return db.list_recent_processes(hours=hours)
    finally:
        conn.close()
