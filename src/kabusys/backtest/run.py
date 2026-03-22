"""CLI entry point.

Usage:
    python -m kabusys.backtest.run \\
        --start 2023-01-01 --end 2024-12-31 \\
        --cash 10000000 --db path/to/kabusys.duckdb

Prerequisite:
    The specified DB file must be pre-populated with prices_daily, features, ai_scores,
    market_regime, and market_calendar.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

logger = logging.getLogger(__name__)


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
    parser.add_argument("--cash", type=float, default=10_000_000, help="Initial cash (JPY) [default: 10000000]")
    parser.add_argument("--slippage", type=float, default=0.001, help="Slippage rate [default: 0.001]")
    parser.add_argument("--commission", type=float, default=0.00055, help="Commission rate [default: 0.00055]")
    parser.add_argument("--max-position-pct", type=float, default=0.20,
                        help="Max position size as %% of portfolio per security [default: 0.20]")
    parser.add_argument("--db", required=True, help="DuckDB file path")
    args = parser.parse_args()

    try:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    except ValueError as exc:
        print(f"ERROR: Invalid date format: {exc}", file=sys.stderr)
        sys.exit(1)

    if start_date >= end_date:
        print("ERROR: --start must be before --end", file=sys.stderr)
        sys.exit(1)

    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest

    conn = init_schema(args.db)
    try:
        result = run_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            initial_cash=args.cash,
            slippage_rate=args.slippage,
            commission_rate=args.commission,
            max_position_pct=args.max_position_pct,
        )
    finally:
        conn.close()

    m = result.metrics
    print(f"\n{'='*40}")
    print(f"  Backtest Result  {start_date} → {end_date}")
    print(f"{'='*40}")
    print(f"  CAGR           : {m.cagr:+.2%}")
    print(f"  Sharpe Ratio   : {m.sharpe_ratio:.3f}")
    print(f"  Max Drawdown   : {m.max_drawdown:.2%}")
    print(f"  Win Rate       : {m.win_rate:.2%}")
    print(f"  Payoff Ratio   : {m.payoff_ratio:.3f}")
    print(f"  Total Trades   : {m.total_trades}")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
