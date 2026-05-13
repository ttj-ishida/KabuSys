# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.execution.order_repository import init_position_entries_db
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.operations.process_registry import register_process, update_process
from kabusys.strategy.signal_generator import generate_signals
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="strategy_signal", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "strategy_signal_job"
_APP_NAME = "strategy_signal"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    sqlite_conn = None
    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path), timeout=30.0)
        init_position_entries_db(sqlite_conn)
        target_date = date.today()
        n = generate_signals(conn, target_date, sqlite_conn=sqlite_conn)
        _updated_rows["signals"] = n
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
    except Exception as exc:
        logger.exception("generate_signals が失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        if sqlite_conn is not None:
            sqlite_conn.close()

    finished_at = datetime.now(timezone.utc)
    try:
        write_job_result(
            JobRunResult(
                job_name=_JOB_NAME,
                status="failed" if _failed else "success",
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=(finished_at - started_at).total_seconds(),
                updated_rows=_updated_rows,
                warnings=[],
                errors=_errors,
            )
        )
    except Exception:
        logger.warning("JobRunResult の書き出しに失敗しました", exc_info=True)

    if run_id is not None:
        try:
            update_process(run_id, status="failed" if _failed else "success")
        except Exception:
            logger.warning("process_registry 更新に失敗しました", exc_info=True)

    log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
