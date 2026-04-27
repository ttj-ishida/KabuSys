"""Signal Queue Confirmation View エントリーポイント。

使用方法:
    python -m kabusys.run_signal_queue_report
    python -m kabusys.run_signal_queue_report --date 2026-04-28
    python -m kabusys.run_signal_queue_report --save
    python -m kabusys.run_signal_queue_report --json
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

import duckdb

from kabusys.config import Settings
from kabusys.operations.signal_queue_report import (
    build_report,
    collect_signals,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Signal Queue Confirmation View を生成する"
    )
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="対象日（省略時は今日）",
    )
    parser.add_argument(
        "--save", action="store_true", help="artifacts/signal_queue/ に保存する"
    )
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        signals = collect_signals(conn, args.date)
    finally:
        conn.close()

    report = build_report(signals, report_date=args.date)

    if args.json:
        print(format_json(report))
    else:
        print(format_cli_summary(report))

    if args.save:
        run_dir = save_report(report)
        dest_msg = f"保存先: {run_dir}"
        if args.json:
            sys.stderr.write(dest_msg + "\n")
        else:
            print(dest_msg)

    return 0 if report.status == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
