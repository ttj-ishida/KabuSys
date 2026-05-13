"""scripts/run_pre_market_report.py

Pre-Market Report の生成ランナー（Task Scheduler 用）。

毎朝 08:00 に自動実行し、レポートを生成・保存した上で LINE 通知を送信する。
手動実行も可能（引数なし）。

Task Scheduler 登録:
    KabuSys_PreMarketReport  08:00  -> scripts/run_pre_market_report.py
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
from kabusys.operations.line_reports import format_pre_market_message
from kabusys.operations.notifier import build_notifier
from kabusys.operations.pre_market_collector import collect
from kabusys.operations.pre_market_report import build_report, format_cli_summary, save_report
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="pre_market_report", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "pre_market_report_job"
_APP_NAME = "pre_market_report"
_BASE = Path(__file__).resolve().parent.parent
_STOP_FLAG = _BASE / "data" / "stop_requested.flag"
_TASK_NAME = "KabuSys_ExecutionStart"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)

    _failed = False
    settings = Settings()
    today = date.today()
    duckdb_conn = None
    sqlite_conn = None
    try:
        duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
        sqlite_conn = sqlite3.connect(f"file:{settings.sqlite_path}?mode=ro", uri=True)

        data = collect(
            duckdb_conn=duckdb_conn,
            sqlite_conn=sqlite_conn,
            stop_flag_path=_STOP_FLAG,
            task_name=_TASK_NAME,
            today=today,
        )

        report = build_report(
            report_date=today,
            data_freshness_ok=data.data_freshness_ok,
            signal_queue_pending=data.signal_queue_pending,
            position_count=data.position_count,
            stop_flag_exists=data.stop_flag_exists,
            task_scheduler_ready=data.task_scheduler_ready,
        )

        saved_path = save_report(report)
        logger.info("レポート保存: %s", saved_path)
        print(format_cli_summary(report))

        # LINE 通知（失敗しても処理継続）
        try:
            notifier = build_notifier(settings)
            msg = format_pre_market_message(
                status=report.status,
                warnings_count=len(report.warnings),
                pending_count=report.signal_queue_pending,
                report_date=today.isoformat(),
            )
            notifier.send(msg)
        except Exception:
            logger.warning("Pre-Market LINE 通知に失敗しました（処理続行）", exc_info=True)

    except Exception:
        logger.exception("pre_market_report バッチが失敗しました")
        _failed = True
    finally:
        if sqlite_conn is not None:
            sqlite_conn.close()
        if duckdb_conn is not None:
            duckdb_conn.close()
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
