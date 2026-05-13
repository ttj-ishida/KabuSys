"""scripts/run_signal_queue_report.py

Signal Queue Report の生成ランナー（Task Scheduler 用）。

毎朝 08:02 に自動実行し、当日の pending シグナルをレポート・保存した上で LINE 通知を送信する。
手動実行も可能（引数なし）。

Task Scheduler 登録:
    KabuSys_SignalQueueReport  08:02  -> scripts/run_signal_queue_report.py
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.operations.line_reports import format_signal_queue_message
from kabusys.operations.notifier import build_notifier
from kabusys.operations.process_registry import register_process, update_process
from kabusys.operations.signal_queue_report import (
    build_report,
    collect_signals,
    format_cli_summary,
    save_report,
)
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="signal_queue_report", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "signal_queue_report_job"
_APP_NAME = "signal_queue_report"


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
    conn = None
    try:
        conn = duckdb.connect(str(settings.duckdb_path), read_only=True)

        signals = collect_signals(conn, today)
        report = build_report(signals, report_date=today)

        saved_path = save_report(report)
        logger.info("レポート保存: %s", saved_path)
        print(format_cli_summary(report))

        # LINE 通知（失敗しても処理継続）
        try:
            notifier = build_notifier(settings)
            msg = format_signal_queue_message(
                status=report.status,
                buy_count=report.buy_count,
                sell_count=report.sell_count,
                signals=report.signals,
                report_date=today.isoformat(),
            )
            notifier.send(msg)
        except Exception:
            logger.warning("Signal Queue LINE 通知に失敗しました（処理続行）", exc_info=True)

    except Exception:
        logger.exception("signal_queue_report バッチが失敗しました")
        _failed = True
    finally:
        if conn is not None:
            conn.close()
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
