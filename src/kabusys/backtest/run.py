"""CLI entry point.

Usage:
    python -m kabusys.backtest.run \\
        --start 2023-01-01 --end 2024-12-31 \\
        --cash 10000000 --db path/to/kabusys.duckdb \\
        --output-format summary

Prerequisite:
    The specified DB file must be pre-populated with prices_daily, features, ai_scores,
    market_regime, and market_calendar.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def _non_negative_int(x: str) -> int:
    v = int(x)
    if v < 0:
        raise argparse.ArgumentTypeError(f"0 以上の整数を指定してください: {x!r}")
    return v


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="KabuSys Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--cash",
        type=float,
        default=10_000_000,
        help="Initial cash (JPY) [default: 10000000]",
    )
    parser.add_argument(
        "--slippage", type=float, default=0.001, help="Slippage rate [default: 0.001]"
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=0.00055,
        help="Commission rate [default: 0.00055]",
    )
    parser.add_argument(
        "--max-position-pct",
        type=float,
        default=0.10,
        help="Max position size as %% of portfolio per security [default: 0.10]",
    )
    parser.add_argument(
        "--allocation-method",
        default="risk_based",
        choices=["equal", "score", "risk_based"],
        help="Capital allocation method [default: risk_based]",
    )
    parser.add_argument(
        "--max-utilization",
        type=float,
        default=0.70,
        help="Max fraction of portfolio to deploy [default: 0.70]",
    )
    parser.add_argument(
        "--max-positions",
        type=int,
        default=10,
        help="Max number of concurrent positions [default: 10]",
    )
    parser.add_argument(
        "--risk-pct",
        type=float,
        default=0.005,
        help="Risk per trade as fraction of portfolio (risk_based only) [default: 0.005]",
    )
    parser.add_argument(
        "--stop-loss-pct",
        type=float,
        default=0.08,
        help="Stop-loss rate for position sizing (risk_based only) [default: 0.08]",
    )
    parser.add_argument(
        "--lot-size",
        type=int,
        default=100,
        help="Lot size (shares per lot) for Japanese stocks [default: 100]",
    )
    parser.add_argument(
        "--scope-mode",
        default="default_universe",
        choices=["default_universe", "manual_codes"],
        help="Backtest scope mode [default: default_universe]",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="Stock codes for manual_codes scope (e.g. --codes 7203 9984)",
    )
    parser.add_argument(
        "--no-preserve-universe-filters",
        action="store_true",
        default=False,
        help=(
            "Diagnostic flag: changes how excluded_reasons are reported for codes "
            "not found in features. When set, missing codes are labeled "
            "'data not available' instead of 'universe filter'. "
            "Does NOT change which codes are actually included in the backtest — "
            "scope filtering is always features-based regardless of this flag."
        ),
    )
    parser.add_argument(
        "--min-holding-days",
        type=_non_negative_int,
        default=5,
        help=(
            "Minimum holding days before non-stop-loss SELL is allowed. "
            "Ignored during bear regime. [default: %(default)s]"
        ),
    )
    parser.add_argument(
        "--max-holding-days",
        type=int,
        default=60,
        help=(
            "Maximum holding days (time exit). Position held this many or more business days "
            "triggers a time_exit SELL regardless of score or min-holding-days. "
            "[default: %(default)s]"
        ),
    )
    parser.add_argument(
        "--trailing-stop-atr",
        type=float,
        default=2.0,
        help="ATR multiplier for trailing stop. Position is sold when close < peak − N×ATR. [default: %(default)s]",
    )
    parser.add_argument("--db", required=True, help="DuckDB file path")
    parser.add_argument(
        "--output-format",
        default="summary",
        choices=["summary", "json", "markdown", "all"],
        help="Output format [default: summary]",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save report files (only used when --output-format=all)",
    )
    args = parser.parse_args()

    try:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    except ValueError as exc:
        logger.error("Invalid date format: %s", exc)
        sys.exit(1)

    if start_date >= end_date:
        logger.error("--start must be before --end")
        sys.exit(1)

    from kabusys.backtest.engine import BacktestScope, run_backtest
    from kabusys.backtest.report import (
        build_report,
        format_cli_summary,
        format_json,
        format_markdown,
        save_report,
    )
    from kabusys.data.schema import init_schema

    conn = init_schema(args.db)
    try:
        scope: BacktestScope | None = None
        if args.scope_mode == "manual_codes":
            if not args.codes:
                logger.error("--codes は --scope-mode=manual_codes のとき必須です")
                sys.exit(1)
            scope = BacktestScope(
                mode="manual_codes",
                codes=args.codes,
                preserve_universe_filters=not args.no_preserve_universe_filters,
            )

        result = run_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            initial_cash=args.cash,
            slippage_rate=args.slippage,
            commission_rate=args.commission,
            max_position_pct=args.max_position_pct,
            allocation_method=args.allocation_method,
            max_utilization=args.max_utilization,
            max_positions=args.max_positions,
            risk_pct=args.risk_pct,
            stop_loss_pct=args.stop_loss_pct,
            lot_size=args.lot_size,
            backtest_scope=scope,
            min_holding_days=args.min_holding_days,
            max_holding_days=args.max_holding_days,
            trailing_stop_atr=args.trailing_stop_atr,
        )
    finally:
        conn.close()

    report = build_report(
        result,
        start_date=start_date,
        end_date=end_date,
        initial_cash=args.cash,
        slippage_rate=args.slippage,
        commission_rate=args.commission,
        allocation_method=args.allocation_method,
        max_position_pct=args.max_position_pct,
        max_utilization=args.max_utilization,
        max_positions=args.max_positions,
        risk_pct=args.risk_pct,
        stop_loss_pct=args.stop_loss_pct,
        lot_size=args.lot_size,
        min_holding_days=getattr(args, "min_holding_days", 5),
        max_holding_days=getattr(args, "max_holding_days", 60),
        trailing_stop_atr=getattr(args, "trailing_stop_atr", 2.0),
    )

    fmt = args.output_format
    if fmt == "summary":
        print(format_cli_summary(report))
    elif fmt == "json":
        print(format_json(report))
    elif fmt == "markdown":
        print(format_markdown(report))
    elif fmt == "all":
        print(format_cli_summary(report))
        run_dir = save_report(report, result, output_dir=args.output_dir)
        logger.info("レポートを保存しました: %s", run_dir)

    # DB 永続化（--output-format に関わらず常に実行）
    from kabusys.backtest.persistence import save_backtest_to_db

    conn_persist = init_schema(str(Path(args.db)))
    try:
        save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        logger.info("バックテスト結果を DB に保存しました: run_id=%s", report.meta.run_id)
    except Exception:
        logger.warning(
            "DB 保存に失敗しました（ファイル保存は完了済み）: run_id=%s",
            report.meta.run_id,
            exc_info=True,
        )
    finally:
        conn_persist.close()


if __name__ == "__main__":
    main()
