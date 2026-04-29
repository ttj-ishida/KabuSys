"""運用成績サマリーレポート エントリーポイント。

使用方法:
    python -m kabusys.run_performance_report --type daily
    python -m kabusys.run_performance_report --type weekly --env paper_trading
    python -m kabusys.run_performance_report --type monthly --from 2026-01-01 --to 2026-04-30
    python -m kabusys.run_performance_report --type daily --save
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

import duckdb

from kabusys.config import Settings
from kabusys.operations.performance_collector import (
    collect_daily_rows,
    collect_monthly_rows,
    collect_weekly_rows,
)
from kabusys.operations.performance_report import (
    build_report,
    format_markdown,
    save_report,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用成績サマリーレポートを生成する")
    parser.add_argument(
        "--type",
        dest="report_type",
        required=True,
        choices=["daily", "weekly", "monthly"],
        help="レポート種別 (daily / weekly / monthly)",
    )
    parser.add_argument(
        "--env",
        default="live",
        choices=["live", "paper_trading"],
        help="対象環境 (live / paper_trading)、省略時は live",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=30),
        metavar="YYYY-MM-DD",
        help="集計開始日（省略時は過去30日）",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="集計終了日（省略時は今日）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="artifacts/performance/ に保存する",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)

    try:
        if args.report_type == "daily":
            rows = collect_daily_rows(conn, args.env, args.from_date, args.to_date)
        elif args.report_type == "weekly":
            rows = collect_weekly_rows(conn, args.env, args.from_date, args.to_date)
        else:
            rows = collect_monthly_rows(conn, args.env, args.from_date, args.to_date)
    finally:
        conn.close()

    report = build_report(
        rows,
        report_type=args.report_type,
        env=args.env,
        from_date=args.from_date,
        to_date=args.to_date,
    )

    print(format_markdown(report))

    if args.save:
        saved_path = save_report(report)
        print(f"\n保存先: {saved_path}")

    return 1 if not rows else 0


if __name__ == "__main__":
    sys.exit(main())
