"""Position Reconciliation View エントリーポイント。

使用方法:
    python -m kabusys.run_position_reconciliation_report
    python -m kabusys.run_position_reconciliation_report --date 2026-04-28
    python -m kabusys.run_position_reconciliation_report --save
    python -m kabusys.run_position_reconciliation_report --json
    python -m kabusys.run_position_reconciliation_report --watch
    python -m kabusys.run_position_reconciliation_report --watch --interval 300
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from datetime import date

from kabusys.config import Settings
from kabusys.execution.broker_factory import BrokerClientFactory
from kabusys.execution.order_repository import OrderRepository
from kabusys.operations.position_reconciliation_report import (
    STATUS_DISCREPANCY,
    build_report,
    collect_position_snapshot,
    format_cli_summary,
    format_json,
    save_report,
)

logger = logging.getLogger(__name__)


def _run_once(settings: Settings, target_date: date, args: argparse.Namespace) -> str:
    """1回のポーリングを実行してステータス文字列を返す。"""
    sqlite_conn = sqlite3.connect(f"file:{settings.sqlite_path}?mode=ro", uri=True)
    broker = None
    try:
        broker = BrokerClientFactory.create(settings)
        repo = OrderRepository(sqlite_conn)
        entries = collect_position_snapshot(broker, repo)
    finally:
        sqlite_conn.close()
        if broker is not None and hasattr(broker, "close"):
            try:
                broker.close()
            except Exception:
                logger.warning("broker.close() で例外が発生しました", exc_info=True)

    report = build_report(entries, report_date=target_date)

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

    return report.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Position Reconciliation View を生成する"
    )
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="レポートの日付ラベル（現在のスナップショットに付与）（省略時は今日）",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="artifacts/position_reconciliation/ に保存する",
    )
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    parser.add_argument(
        "--watch", action="store_true", help="定期ポーリングモードで実行する"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        metavar="N",
        help="--watch 時のポーリング間隔（秒）（デフォルト: 600）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    settings = Settings()
    interval = max(1, args.interval)  # スピンループ防止のため最小 1 秒

    if args.watch:
        while True:
            try:
                _run_once(settings, args.date, args)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("ポーリング中にエラー: %s", e, exc_info=True)
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                break
        return 0

    status = _run_once(settings, args.date, args)
    return 1 if status == STATUS_DISCREPANCY else 0


if __name__ == "__main__":
    sys.exit(main())
