"""scripts/run_manual_order_report.py

手動注文候補レポート（#412）の生成ランナー（スケジューラ / Task Scheduler 用）。

ユーザーが証券画面で手動注文するための BUY/SELL 候補・上限・見送り条件を
artifacts/manual_orders/{date}/{phase}.md / .json に出力する。morning のみ LINE 通知する。
DuckDB は読み取り専用で開き、発注・kabu API 呼び出しは一切行わない。

使用方法:
    python scripts/run_manual_order_report.py --phase evening   # 21:10（夜間バッチ後）
    python scripts/run_manual_order_report.py --phase morning   # 08:05（寄り前）
    python scripts/run_manual_order_report.py --phase morning --date 2026-10-14
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
from kabusys.operations.manual_order_report import PHASES, collect_manual_order_report
from kabusys.operations.manual_order_report_format import (
    format_cli_summary,
    format_line_message,
    save_manual_order_report,
)
from kabusys.operations.notifier import build_notifier
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="manual_order_report", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "manual_order_report_job"
_APP_NAME = "manual_order_report"
_BASE = Path(__file__).resolve().parent.parent
_STOP_FLAG = _BASE / "data" / "stop_requested.flag"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="手動注文候補レポートを生成する（発注はしない）")
    p.add_argument("--phase", choices=PHASES, required=True)
    p.add_argument(
        "--date", type=date.fromisoformat, default=None, help="レポート日 YYYY-MM-DD（既定: 今日）"
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)

    _failed = False
    report_date: date = args.date or date.today()
    conn = None
    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
        manual = settings.manual_trading_enabled
        report = collect_manual_order_report(
            conn,
            phase=args.phase,
            report_date=report_date,
            manual_trading_enabled=manual,
            initial_cash=settings.manual_trading_initial_cash if manual else 0.0,
            portfolio_value=settings.portfolio_value,
            stop_flag_path=_STOP_FLAG,
            sqlite_path=settings.sqlite_path,
        )
        saved = save_manual_order_report(report)
        logger.info("手動注文候補レポート保存: %s", saved)
        print(format_cli_summary(report))

        if args.phase == "morning":
            try:
                build_notifier(settings).send(format_line_message(report))
            except Exception:
                logger.warning(
                    "手動注文レポートの LINE 通知に失敗しました（処理続行）", exc_info=True
                )
    except Exception:
        logger.exception("manual_order_report (%s) が失敗しました", args.phase)
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
