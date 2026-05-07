# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.strategy.signal_generator import generate_signals
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="strategy_signal")
logger = logging.getLogger(__name__)

_JOB_NAME = "strategy_signal_job"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        target_date = date.today()
        n = generate_signals(conn, target_date)
        _updated_rows["signals"] = n
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
    except Exception as exc:
        logger.exception("generate_signals が失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        conn.close()

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

    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
