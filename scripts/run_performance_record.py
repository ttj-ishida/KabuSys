"""scripts/run_performance_record.py

日次成績の記録ジョブ（performance_record_job）。

Task Scheduler から 18:00 に起動される（17:30 の data_update で当日終値が入った後）。
総資産・現金を算出して portfolio_performance に (date, env) 単位で UPSERT する。

資産額の算出元:
    MANUAL_TRADING_ENABLED=true  -> calc_manual_portfolio_value（元手＋手動約定）
    paper_trading / development  -> calc_paper_portfolio_value
    live                         -> 対象外（警告ログのみ・終了コード 0）
非営業日は何も記録しない。`--date YYYY-MM-DD` で対象日を指定できる（既定: 今日）。
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kabusys.config import Settings
from kabusys.data.calendar_management import is_trading_day
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.manual_trades import calc_manual_portfolio_value
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.operations.paper_portfolio import calc_paper_portfolio_value
from kabusys.operations.performance_recorder import record_daily_performance
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="performance_record", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "performance_record_job"
_APP_NAME = "performance_record"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="日次成績を portfolio_performance に記録する")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="記録対象日（省略時: 今日）",
    )
    return parser.parse_args(argv if argv is not None else [])


def record_for_date(settings: Settings, conn: duckdb.DuckDBPyConnection, as_of: date) -> str:
    """as_of の成績を記録し、結果を "recorded" / "skipped_*" で返す。"""
    if not is_trading_day(conn, as_of):
        logger.info("非営業日のため成績を記録しません: %s", as_of)
        return "skipped_non_trading_day"

    if settings.manual_trading_enabled:
        equity, cash = calc_manual_portfolio_value(
            conn, settings.manual_trading_initial_cash, as_of=as_of
        )
    elif settings.is_paper or settings.is_dev:
        equity, cash = calc_paper_portfolio_value(settings, conn, as_of=as_of)
    else:
        logger.warning(
            "env=%s は成績記録の対象外です（live の記録は未対応）。何もしません", settings.env
        )
        return "skipped_live"

    row = record_daily_performance(conn, as_of=as_of, env=settings.env, equity=equity, cash=cash)
    logger.info(
        "成績を記録: date=%s env=%s equity=%.0f cash=%.0f daily_return=%s drawdown=%.4f",
        row.date,
        row.env,
        row.equity,
        row.cash,
        "None" if row.daily_return is None else f"{row.daily_return:.4f}",
        row.drawdown,
    )
    return "recorded"


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    as_of = args.date or date.today()
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)

    failed = False
    errors: list[str] = []
    updated_rows: dict[str, int] = {}
    job_status = "success"
    conn = None
    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))
        result = record_for_date(settings, conn, as_of)
        updated_rows["portfolio_performance"] = 1 if result == "recorded" else 0
        if result != "recorded":
            job_status = "skipped"
    except Exception as exc:
        logger.exception("performance_record バッチが失敗しました")
        failed = True
        job_status = "failed"
        errors.append(str(exc))
    finally:
        if conn is not None:
            conn.close()
        if run_id is not None:
            try:
                update_process(run_id, status="failed" if failed else "success")
            except Exception:
                logger.warning("process_registry 更新に失敗しました", exc_info=True)
        finished_at = datetime.now(timezone.utc)
        try:
            write_job_result(
                JobRunResult(
                    job_name=_JOB_NAME,
                    status=job_status,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_sec=(finished_at - started_at).total_seconds(),
                    updated_rows=updated_rows,
                    warnings=[],
                    errors=errors,
                )
            )
        except Exception:
            logger.warning("JobRunResult の書き出しに失敗しました", exc_info=True)
        log_run_end(_APP_NAME, status="failed" if failed else "success", started_at=started_at)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
