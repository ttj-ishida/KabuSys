"""Market Close Summary エントリーポイント。

使用方法:
    python -m kabusys.run_market_close_report
    python -m kabusys.run_market_close_report --date 2026-04-28
    python -m kabusys.run_market_close_report --save
    python -m kabusys.run_market_close_report --json
    python -m kabusys.run_market_close_report --save --json
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
from kabusys.operations.market_close_collector import collect_market_close_data
from kabusys.operations.market_close_report import (
    STATUS_BLOCKED,
    build_report,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def _sqlite_path(settings: Settings) -> Path:
    """run_execution と同じく、paper_trading では paper 用 SQLite を使う（Issue #413）。"""
    return Path(settings.paper_sqlite_path if settings.is_paper else settings.sqlite_path)


def _open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    """SQLite を read-only で開く。ファイルがなければ空のインメモリ DB を返す（作成しない）。"""
    if not path.exists():
        logger.warning("SQLite が見つかりません（Execution 未起動）: %s", path)
        return sqlite3.connect(":memory:")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Market Close Summary を生成する")
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="レポートの日付ラベル兼クエリ対象日（省略時は今日）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="artifacts/market_close/ に保存する",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 形式で出力する",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    sqlite_conn = _open_sqlite_readonly(_sqlite_path(settings))

    try:
        data = collect_market_close_data(duckdb_conn, sqlite_conn, args.date)
    finally:
        duckdb_conn.close()
        sqlite_conn.close()

    report = build_report(
        report_date=args.date,
        signal_pending_count=data.signal_pending_count,
        positions_updated=data.positions_updated,
        performance_recorded=data.performance_recorded,
        filled_count=data.filled_count,
        daily_return=data.daily_return,
        equity_today=data.equity_today,
        equity_prev=data.equity_prev,
    )

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

    return 1 if report.status == STATUS_BLOCKED else 0


if __name__ == "__main__":
    sys.exit(main())
