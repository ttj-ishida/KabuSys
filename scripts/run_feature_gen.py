# scripts/run_feature_gen.py
"""Night batch: 特徴量生成 (feature_generation_job)。

Task Scheduler から 16:00 に起動される。
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
from kabusys.strategy.feature_engineering import build_features
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

setup_logging(app_name="feature_gen")
logger = logging.getLogger(__name__)

_JOB_NAME = "feature_generation_job"
_APP_NAME = "feature_gen"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        target_date = date.today()
        n = build_features(conn, target_date)
        _updated_rows["features"] = n
        logger.info("特徴量生成完了: %d 件 (date=%s)", n, target_date)
    except Exception as exc:
        logger.exception("build_features が失敗しました")
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

    log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
