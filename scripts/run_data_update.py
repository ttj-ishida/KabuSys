# scripts/run_data_update.py
"""Night batch: 日次市場データ更新 (data_update_job)。

Task Scheduler から 17:30 に起動される。
J-Quants の日足データは 16:30〜17:00 頃に公開されるため、
17:30 に実行することで当日データを確実に取得できる。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.breadth import calc_and_save_breadth
from kabusys.data.pipeline import run_daily_etl
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="data_update")
logger = logging.getLogger(__name__)

_JOB_NAME = "data_update_job"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    _failed = False
    _has_warnings = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        result = run_daily_etl(conn)
        _updated_rows["prices_daily"] = result.prices_saved
        _updated_rows["fundamentals"] = result.financials_saved
        if result.errors:
            logger.warning("ETL 完了（エラーあり）: %s", result.errors)
            _errors.extend(result.errors)
            _has_warnings = True
        else:
            logger.info("ETL 完了")

        max_date_row = conn.execute("SELECT MAX(date) FROM prices_daily").fetchone()
        if max_date_row and max_date_row[0]:
            target_date = max_date_row[0]
            breadth_result = calc_and_save_breadth(conn, target_date)
            _updated_rows["market_breadth"] = breadth_result
            if breadth_result == 1:
                logger.info("breadth 挿入完了: date=%s", target_date)
            else:
                logger.info("breadth スキップ（既存 or データ不足）: date=%s", target_date)
        else:
            logger.warning("breadth 計算スキップ: prices_daily にデータなし")
    except Exception as exc:
        logger.exception("data_update バッチが失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        conn.close()

    finished_at = datetime.now(timezone.utc)
    try:
        write_job_result(
            JobRunResult(
                job_name=_JOB_NAME,
                status="failed" if _failed else ("warning" if _has_warnings else "success"),
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
