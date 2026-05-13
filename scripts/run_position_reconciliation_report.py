"""scripts/run_position_reconciliation_report.py

Position Reconciliation Report の生成ランナー（Task Scheduler 用）。

毎朝 08:05 に自動実行し、ブローカーとローカル DB のポジション差分を検出・保存した上で
LINE 通知を送信する。DISCREPANCY 検出時は緊急アラートとして通知する。
手動実行も可能（引数なし）。

Task Scheduler 登録:
    KabuSys_PositionReconciliationReport  08:05  -> scripts/run_position_reconciliation_report.py
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.order_repository import OrderRepository
from kabusys.operations.line_reports import format_position_reconciliation_message
from kabusys.operations.notifier import build_notifier
from kabusys.operations.position_reconciliation_report import (
    build_report,
    collect_position_snapshot,
    format_cli_summary,
    save_report,
)
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="position_reconciliation_report", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "position_reconciliation_report_job"
_APP_NAME = "position_reconciliation_report"


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
    sqlite_conn = None
    broker = None
    try:
        sqlite_uri = Path(settings.sqlite_path).resolve().as_uri() + "?mode=ro"
        sqlite_conn = sqlite3.connect(sqlite_uri, uri=True)
        broker = BrokerClientFactory.create(settings)
        repo = OrderRepository(sqlite_conn)

        entries = collect_position_snapshot(broker, repo)
        report = build_report(entries, report_date=today)

        saved_path = save_report(report)
        logger.info("レポート保存: %s", saved_path)
        print(format_cli_summary(report))

        # LINE 通知（失敗しても処理継続）
        try:
            notifier = build_notifier(settings)
            msg = format_position_reconciliation_message(
                status=report.status,
                total_count=report.total_count,
                mismatch_count=report.mismatch_count,
                positions=report.positions,
                report_date=today.isoformat(),
            )
            notifier.send(msg)
        except Exception:
            logger.warning(
                "Position Reconciliation LINE 通知に失敗しました（処理続行）", exc_info=True
            )

    except Exception:
        logger.exception("position_reconciliation_report バッチが失敗しました")
        _failed = True
    finally:
        if sqlite_conn is not None:
            sqlite_conn.close()
        if broker is not None and hasattr(broker, "close"):
            try:
                broker.close()
            except Exception:
                logger.warning("broker.close() で例外が発生しました", exc_info=True)
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
