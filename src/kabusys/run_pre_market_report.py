"""
Pre-Market Report エントリーポイント。

使用方法:
    python -m kabusys.run_pre_market_report
    python -m kabusys.run_pre_market_report --save
    python -m kabusys.run_pre_market_report --json
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date
from pathlib import Path

import duckdb

from kabusys.config import Settings
from kabusys.operations.pre_market_collector import collect
from kabusys.operations.pre_market_report import (
    build_report,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)

_STOP_FLAG = Path(__file__).resolve().parents[2] / "data" / "stop_requested.flag"
_TASK_NAME = "KabuSys_ExecutionStart"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-Market Report を生成する")
    parser.add_argument(
        "--save", action="store_true", help="artifacts/pre_market/ に保存する"
    )
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    today = date.today()

    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))

    try:
        data = collect(
            duckdb_conn=duckdb_conn,
            sqlite_conn=sqlite_conn,
            stop_flag_path=_STOP_FLAG,
            task_name=_TASK_NAME,
            today=today,
        )
    finally:
        duckdb_conn.close()
        sqlite_conn.close()

    report = build_report(
        report_date=today,
        data_freshness_ok=data.data_freshness_ok,
        signal_queue_pending=data.signal_queue_pending,
        position_count=data.position_count,
        stop_flag_exists=data.stop_flag_exists,
        task_scheduler_ready=data.task_scheduler_ready,
    )

    if args.json:
        print(format_json(report))
    else:
        print(format_cli_summary(report))

    if args.save:
        run_dir = save_report(report)
        print(f"保存先: {run_dir}")

    return 0 if report.status != "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
