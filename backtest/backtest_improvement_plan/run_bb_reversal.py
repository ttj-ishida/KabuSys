"""BB逆張り戦略バックテスト調査スクリプト

Close < Lower Band でエントリー、Close >= Middle Band で利確。
generate_signals() / 既存戦略コードへの変更なし。

Usage:
    python backtest/backtest_improvement_plan/run_bb_reversal.py \
        --db data/kabusys.duckdb \
        --start 2017-01-01 --end 2025-12-31
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics  # noqa: E402
from kabusys.backtest.simulator import PortfolioSimulator  # noqa: E402
from kabusys.data.calendar_management import get_trading_days  # noqa: E402
from kabusys.portfolio import (  # noqa: E402
    calc_equal_weights,
    calc_position_sizes,
    select_candidates,
)

logger = logging.getLogger(__name__)

SCENARIOS: list[dict] = [
    {"id": "BB1_base", "period": 20, "sigma": 2.0, "regime_filter": False},
    {"id": "BB2_tight", "period": 20, "sigma": 1.5, "regime_filter": False},
    {"id": "BB3_wide", "period": 20, "sigma": 2.5, "regime_filter": False},
    {"id": "BB4_base_regime", "period": 20, "sigma": 2.0, "regime_filter": True},
    {"id": "BB5_tight_regime", "period": 20, "sigma": 1.5, "regime_filter": True},
]


def _compute_bb_rows(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
    period: int,
    sigma: float,
) -> list[tuple[str, float, float, float]]:
    """指定日の全銘柄について BB バンド値を計算して返す。

    Returns: [(code, close, lower_band, middle_band), ...]
    period 日分の履歴が不足する銘柄、std=0 の銘柄は除外する。
    """
    lookback_start = trading_day - timedelta(days=period * 5)
    rows = conn.execute(
        f"""
        WITH filtered AS (
            SELECT code, date, CAST(close AS DOUBLE) AS close
            FROM prices_daily
            WHERE date >= ? AND date <= ?
        ),
        bb AS (
            SELECT
                code, date, close,
                AVG(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS middle_band,
                STDDEV_POP(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS std_close,
                COUNT(*) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS row_cnt
            FROM filtered
        )
        SELECT code, close,
               middle_band - ? * std_close AS lower_band,
               middle_band
        FROM bb
        WHERE date = ?
          AND row_cnt >= ?
          AND std_close > 0
        """,
        [lookback_start, trading_day, sigma, trading_day, period],
    ).fetchall()
    return [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows]


def _generate_buy_signals(
    bb_rows: list[tuple[str, float, float, float]],
    universe_codes: set[str],
    held_codes: set[str],
) -> list[dict]:
    """BB 下バンド下抜けで BUY シグナルを生成する。

    Args:
        bb_rows:       [(code, close, lower_band, middle_band), ...]
        universe_codes: features テーブルに存在する銘柄コードセット。
        held_codes:    現在保有中（SELL 対象除外後）の銘柄コードセット。

    Returns:
        [{"code", "score": 1.0, "signal_rank": int, "size_multiplier": 1.0}, ...]
    """
    candidates = [
        code
        for code, close, lower_band, _ in bb_rows
        if close < lower_band and code in universe_codes and code not in held_codes
    ]
    return [
        {"code": code, "score": 1.0, "signal_rank": rank, "size_multiplier": 1.0}
        for rank, code in enumerate(candidates, 1)
    ]


def _generate_sell_signals(
    close_prices: dict[str, float],
    positions: dict[str, int],
    cost_basis: dict[str, float],
    held_trading_days: dict[str, int],
    middle_bands: dict[str, float],
    stop_loss_rate: float,
    max_holding_days: int,
) -> list[dict]:
    """保有ポジションに対してエグジット条件を判定し SELL シグナルを返す。

    優先順位:
      1. ストップロス: pnl_rate <= -stop_loss_rate
      2. 時間決済: held_trading_days >= max_holding_days
      3. 利確（中心線回帰）: close >= middle_band
    """
    sell_signals: list[dict] = []
    for code, shares in positions.items():
        if shares <= 0:
            continue
        close = close_prices.get(code)
        if close is None:
            continue
        avg_price = cost_basis.get(code, 0.0)
        if avg_price <= 0:
            continue

        pnl_rate = (close - avg_price) / avg_price
        if pnl_rate <= -stop_loss_rate:
            sell_signals.append({"code": code})
            continue

        if held_trading_days.get(code, 0) >= max_holding_days:
            sell_signals.append({"code": code})
            continue

        middle = middle_bands.get(code)
        if middle is not None and close >= middle:
            sell_signals.append({"code": code})

    return sell_signals


def _is_buy_blocked_by_regime(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> bool:
    """レジームフィルター: 市場全体が下降トレンドなら買いをブロック。

    以下のいずれかの条件が真なら True（買いブロック）を返す:
      - market_breadth テーブルに対象日の行があり breadth_stop = True
      - market_regime テーブルに対象日の行があり label = 'bear'

    テーブルや行が存在しない場合は False（買い許可）を返す。

    Args:
        conn: DuckDB 接続
        trading_day: 判定対象日

    Returns:
        True = 買いブロック, False = 買い許可
    """
    try:
        row = conn.execute(
            "SELECT breadth_stop FROM market_breadth WHERE date = ?",
            [trading_day],
        ).fetchone()
        if row is not None and row[0]:
            return True
    except Exception:
        pass
    try:
        row = conn.execute(
            "SELECT label FROM market_regime WHERE date = ?",
            [trading_day],
        ).fetchone()
        if row is not None and row[0] == "bear":
            return True
    except Exception:
        pass
    return False


def run_bb_scenario(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    period: int,
    sigma: float,
    use_regime_filter: bool,
    initial_cash: float = 10_000_000,
    max_positions: int = 5,
    max_position_pct: float = 0.20,
    max_utilization: float = 0.70,
    stop_loss_rate: float = 0.08,
    max_holding_days: int = 20,
    lot_size: int = 100,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
) -> "BacktestMetrics":
    """BB 逆張りシナリオのシミュレーションループを実行し評価指標を返す。

    Args:
        conn:              DuckDB 接続。
        start_date:        バックテスト開始日。
        end_date:          バックテスト終了日。
        period:            BB 計算期間（日数）。
        sigma:             BB バンド幅（標準偏差の倍率）。
        use_regime_filter: True の場合、下降トレンド時に BUY をブロックする。
        initial_cash:      初期資金（円）。
        max_positions:     最大保有銘柄数。
        max_position_pct:  1 銘柄の最大配分比率（総資産比）。
        max_utilization:   投下資金上限（総資産比）。
        stop_loss_rate:    ストップロス率。
        max_holding_days:  最大保有日数。
        lot_size:          単元株数。
        slippage_rate:     スリッページ率。
        commission_rate:   手数料率。

    Returns:
        BacktestMetrics インスタンス。
    """
    sim = PortfolioSimulator(initial_cash=initial_cash)
    held_trading_days: dict[str, int] = {}
    next_day_orders: list[dict] = []

    trading_days = get_trading_days(conn, start_date, end_date)
    logger.info(
        "run_bb_scenario: start=%s end=%s period=%d sigma=%.1f regime=%s days=%d",
        start_date,
        end_date,
        period,
        sigma,
        use_regime_filter,
        len(trading_days),
    )

    for trading_day in trading_days:
        # Step 1: Execute previous orders at today's open
        open_rows = conn.execute(
            "SELECT code, CAST(open AS DOUBLE) FROM prices_daily WHERE date = ?",
            [trading_day],
        ).fetchall()
        open_prices = {code: p for code, p in open_rows if p is not None}

        prev_positions = set(sim.positions)
        sim.execute_orders(
            next_day_orders,
            open_prices,
            slippage_rate,
            commission_rate,
            trading_day,
            lot_size=lot_size,
        )
        new_holdings = set(sim.positions) - prev_positions
        closed_holdings = prev_positions - set(sim.positions)
        for code in new_holdings:
            held_trading_days[code] = 1
        for code in closed_holdings:
            held_trading_days.pop(code, None)
        for code in sim.positions:
            if code not in new_holdings:
                held_trading_days[code] = held_trading_days.get(code, 0) + 1

        # Step 2: Mark to market with today's close
        close_rows = conn.execute(
            "SELECT code, CAST(close AS DOUBLE) FROM prices_daily WHERE date = ?",
            [trading_day],
        ).fetchall()
        close_prices = {code: p for code, p in close_rows if p is not None}
        sim.mark_to_market(trading_day, close_prices)

        # Step 3: BB bands + universe
        bb_rows = _compute_bb_rows(conn, trading_day, period, sigma)
        universe_rows = conn.execute(
            "SELECT DISTINCT code FROM features WHERE date = ?", [trading_day]
        ).fetchall()
        universe_codes = {r[0] for r in universe_rows}
        middle_bands = {code: middle for code, close, lower, middle in bb_rows}

        # Step 4: SELL signals
        sell_signals = _generate_sell_signals(
            close_prices=close_prices,
            positions=dict(sim.positions),
            cost_basis=dict(sim.cost_basis),
            held_trading_days=held_trading_days,
            middle_bands=middle_bands,
            stop_loss_rate=stop_loss_rate,
            max_holding_days=max_holding_days,
        )
        sell_codes = {s["code"] for s in sell_signals}

        # Step 5: BUY signals
        buy_blocked = use_regime_filter and _is_buy_blocked_by_regime(conn, trading_day)
        if buy_blocked:
            buy_signals: list[dict] = []
        else:
            held_codes = set(sim.positions) - sell_codes
            buy_signals = _generate_buy_signals(bb_rows, universe_codes, held_codes)

        # Step 6: Position sizing
        current_pv = sim.history[-1].portfolio_value
        candidates = select_candidates(buy_signals, max_positions=max_positions)
        weights = calc_equal_weights(candidates)
        available_cash = min(sim.cash, current_pv * max_utilization)
        sized = calc_position_sizes(
            weights=weights,
            candidates=candidates,
            portfolio_value=current_pv,
            available_cash=available_cash,
            current_positions=sim.positions,
            open_prices=close_prices,
            allocation_method="equal",
            risk_pct=0.005,
            stop_loss_pct=stop_loss_rate,
            max_position_pct=max_position_pct,
            max_utilization=max_utilization,
            cost_buffer=slippage_rate + commission_rate,
            lot_size=lot_size,
        )

        # Step 7: Queue next day's orders
        next_day_orders = [
            {"code": code, "side": "buy", "shares": (int(shares) // lot_size) * lot_size}
            for code, shares in sized.items()
            if shares > 0 and code not in sell_codes
        ]
        next_day_orders = [o for o in next_day_orders if o["shares"] > 0]
        next_day_orders += [{"code": s["code"], "side": "sell"} for s in sell_signals]

    return calc_metrics(sim.history, sim.trades)


# ---------------------------------------------------------------------------
# 出力・CLI
# ---------------------------------------------------------------------------


def _print_results_table(results: list[dict]) -> None:
    header = (
        f"{'scenario':<22} {'CAGR':>7} {'Sharpe':>7} {'MaxDD':>7}"
        f" {'WinRate':>8} {'PF':>6} {'Trades':>7} {'AvgHold':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        m: BacktestMetrics = r["metrics"]
        print(
            f"{r['id']:<22}"
            f" {m.cagr * 100:>+6.1f}%"
            f" {m.sharpe_ratio:>7.3f}"
            f" {m.max_drawdown * 100:>6.1f}%"
            f" {m.win_rate * 100:>7.1f}%"
            f" {m.profit_factor:>6.2f}"
            f" {m.total_trades:>7d}"
            f" {m.avg_holding_days:>7.1f}d"
        )


def _save_csv(results: list[dict], output_dir: Path) -> Path:
    from datetime import datetime

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"bb_reversal_{ts}.csv"
    fieldnames = [
        "scenario",
        "period",
        "sigma",
        "regime_filter",
        "cagr",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "payoff_ratio",
        "profit_factor",
        "total_trades",
        "annual_volatility",
        "calmar_ratio",
        "avg_holding_days",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            m: BacktestMetrics = r["metrics"]
            writer.writerow(
                {
                    "scenario": r["id"],
                    "period": r["period"],
                    "sigma": r["sigma"],
                    "regime_filter": r["regime_filter"],
                    "cagr": round(m.cagr, 6),
                    "sharpe_ratio": round(m.sharpe_ratio, 6),
                    "max_drawdown": round(m.max_drawdown, 6),
                    "win_rate": round(m.win_rate, 6),
                    "payoff_ratio": round(m.payoff_ratio, 6),
                    "profit_factor": round(m.profit_factor, 6),
                    "total_trades": m.total_trades,
                    "annual_volatility": round(m.annual_volatility, 6),
                    "calmar_ratio": round(m.calmar_ratio, 6),
                    "avg_holding_days": round(m.avg_holding_days, 2),
                }
            )
    return path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="BB逆張り戦略バックテスト調査")
    parser.add_argument("--db", required=True, help="DuckDB ファイルパス")
    parser.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10_000_000)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--output-dir", default="artifacts")
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    conn = duckdb.connect(args.db, read_only=True)
    try:
        results = []
        for scenario in SCENARIOS:
            print(f"\n>> Running {scenario['id']} ...")
            metrics = run_bb_scenario(
                conn=conn,
                start_date=start_date,
                end_date=end_date,
                period=scenario["period"],
                sigma=scenario["sigma"],
                use_regime_filter=scenario["regime_filter"],
                initial_cash=args.cash,
                max_positions=args.max_positions,
            )
            results.append({**scenario, "metrics": metrics})
        print("\n" + "=" * 70)
        _print_results_table(results)
        csv_path = _save_csv(results, Path(args.output_dir))
        print(f"\nCSV 保存: {csv_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
