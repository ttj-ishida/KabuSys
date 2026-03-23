# src/kabusys/backtest/engine.py
"""
バックテストエンジン。

BacktestFramework.md Section 6〜8 に従い、全体ループと補助関数を提供する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import DailySnapshot, PortfolioSimulator, TradeRecord
from kabusys.portfolio import (
    apply_sector_cap,
    calc_equal_weights,
    calc_position_sizes,
    calc_regime_multiplier,
    calc_score_weights,
    select_candidates,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """run_backtest() の戻り値。"""

    history: list[DailySnapshot]
    trades: list[TradeRecord]
    metrics: BacktestMetrics


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def _build_backtest_conn(
    source_conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
) -> duckdb.DuckDBPyConnection:
    """本番 DB からインメモリ DuckDB にデータをコピーしてバックテスト用接続を返す。

    本番 DB の signals / positions テーブルを汚染しない。
    シグナル生成に必要な features 等は start_date - 300日 から end_date までコピーする。

    Args:
        source_conn: 本番 DuckDB 接続（読み取り専用で使用）。
        start_date:  バックテスト開始日。
        end_date:    バックテスト終了日。

    Returns:
        init_schema(":memory:") 済みのインメモリ接続。
    """
    from kabusys.data.schema import init_schema

    bt_conn = init_schema(":memory:")
    data_start = start_date - timedelta(days=300)

    # 日付範囲でフィルタするテーブル
    date_filtered_tables = ("prices_daily", "features", "ai_scores", "market_regime")
    for table in date_filtered_tables:
        try:
            rows = source_conn.execute(
                f"SELECT * FROM {table} WHERE date >= ? AND date <= ?",
                [data_start, end_date],
            ).fetchall()
            if not rows:
                continue
            result = source_conn.execute(f"SELECT * FROM {table} LIMIT 0")
            cols = [desc[0] for desc in result.description]
            col_list = ", ".join(cols)
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})", rows
            )
        except Exception as exc:
            logger.warning("_build_backtest_conn: %s のコピーをスキップ: %s", table, exc)

    # market_calendar は全件コピー
    try:
        rows = source_conn.execute("SELECT * FROM market_calendar").fetchall()
        if rows:
            result = source_conn.execute("SELECT * FROM market_calendar LIMIT 0")
            cols = [desc[0] for desc in result.description]
            col_list = ", ".join(cols)
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT INTO market_calendar ({col_list}) VALUES ({placeholders})", rows
            )
    except Exception as exc:
        logger.warning("_build_backtest_conn: market_calendar のコピーをスキップ: %s", exc)

    # stocks は全件コピー（銘柄のセクターは日付フィルタなし）
    # TIMESTAMPTZ 型の updated_at 列は pytz 依存のため除外し、明示列のみコピーする
    try:
        rows = source_conn.execute(
            "SELECT code, name, market, sector FROM stocks"
        ).fetchall()
        if rows:
            bt_conn.executemany(
                "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
                rows,
            )
    except Exception as exc:
        logger.warning("_build_backtest_conn: stocks のコピーをスキップ: %s", exc)

    return bt_conn


def _fetch_open_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄始値を {code: open} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(open AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _fetch_close_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄終値を {code: close} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(close AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _write_positions(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
    positions: dict[str, int],
    cost_basis: dict[str, float],
) -> None:
    """シミュレータの保有状態を positions テーブルに書き戻す（冪等）。

    generate_signals() の _generate_sell_signals() が positions テーブルを読むため、
    シグナル生成の直前に呼び出す必要がある。
    market_value は NULL で挿入（nullable カラム、SELL 判定では参照しない）。

    Args:
        positions:  code → 株数（0株の銘柄は書き込まない）。
        cost_basis: code → 平均取得単価。
    """
    conn.execute("DELETE FROM positions WHERE date = ?", [trading_day])
    rows = [
        (trading_day, code, shares, cost_basis.get(code, 0.0))
        for code, shares in positions.items()
        if shares > 0
    ]
    if rows:
        conn.executemany(
            "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
            "VALUES (?, ?, ?, ?, NULL)",
            rows,
        )


def _read_day_signals(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> tuple[list[dict], list[dict]]:
    """指定日の signals テーブルから BUY / SELL シグナルを読み取る。

    Returns:
        (buy_signals, sell_signals)
        buy_signals:  [{"code": str, "signal_rank": int, "score": float}, ...]
        sell_signals: [{"code": str}, ...]
    """
    buy_rows = conn.execute(
        "SELECT code, signal_rank, score FROM signals "
        "WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [trading_day],
    ).fetchall()
    sell_rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
        [trading_day],
    ).fetchall()
    buy_signals = [{"code": row[0], "signal_rank": row[1], "score": row[2] or 0.0} for row in buy_rows]
    sell_signals = [{"code": row[0]} for row in sell_rows]
    return buy_signals, sell_signals


def _fetch_regime(conn: duckdb.DuckDBPyConnection, trading_day: date) -> str:
    """market_regime テーブルから当日レジームを返す。データなしなら 'bull' でフォールバック。

    schema.py の market_regime テーブルのレジーム列名は `regime_label`。
    """
    row = conn.execute(
        "SELECT regime_label FROM market_regime WHERE date = ?", [trading_day]
    ).fetchone()
    if row is None:
        logger.warning(
            "_fetch_regime: %s のレジームが取得できません。'bull' でフォールバック。", trading_day
        )
        return "bull"
    return row[0]


def _fetch_sector_map(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """stocks テーブルから {code: sector} を返す。テーブルが空なら {}。"""
    rows = conn.execute(
        "SELECT code, sector FROM stocks WHERE sector IS NOT NULL"
    ).fetchall()
    return {code: sector for code, sector in rows}


# ---------------------------------------------------------------------------
# パブリック API
# ---------------------------------------------------------------------------

def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    max_positions: int = 10,
    allocation_method: str = "risk_based",
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
) -> BacktestResult:
    """バックテストを実行し結果を返す。

    Args:
        conn:              本番 DuckDB 接続（読み取り専用で使用）。
        start_date:        バックテスト開始日（含む）。
        end_date:          バックテスト終了日（含む）。
        initial_cash:      初期資金（円）。
        slippage_rate:     スリッページ率（デフォルト 0.1%）。
        commission_rate:   手数料率（デフォルト 0.055%）。
        max_position_pct:  1銘柄あたりの最大ポートフォリオ比率（デフォルト 10%）。
        max_utilization:   全ポジション投下上限（デフォルト 70%）。
        max_positions:     最大保有銘柄数（デフォルト 10）。
        allocation_method: 資金配分方式: "equal" | "score" | "risk_based"（デフォルト）。
        risk_pct:          1トレード許容リスク率（risk_based 時、デフォルト 0.5%）。
        stop_loss_pct:     損切り率（株数計算用、risk_based 時、デフォルト 8%）。

    Returns:
        BacktestResult（history, trades, metrics）。
    """
    from kabusys.data.calendar_management import get_trading_days
    from kabusys.strategy.signal_generator import generate_signals

    bt_conn = _build_backtest_conn(conn, start_date, end_date)
    simulator = PortfolioSimulator(initial_cash=initial_cash)
    signals_prev: list[dict] = []

    try:
        trading_days = get_trading_days(bt_conn, start_date, end_date)
        logger.info(
            "run_backtest: 開始 start=%s end=%s 営業日数=%d 初期資金=%.0f allocation=%s",
            start_date, end_date, len(trading_days), initial_cash, allocation_method,
        )

        # sector_map はバックテスト開始前に一度だけ取得（銘柄のセクターは日次変化しない）
        sector_map = _fetch_sector_map(bt_conn)

        for trading_day in trading_days:
            # Step 1: 前日シグナルを当日 open で約定
            open_prices = _fetch_open_prices(bt_conn, trading_day)
            simulator.execute_orders(signals_prev, open_prices, slippage_rate, commission_rate, trading_day)

            # Step 2: positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
            _write_positions(bt_conn, trading_day, simulator.positions, simulator.cost_basis)

            # Step 3: 終値で時価評価・スナップショット記録
            close_prices = _fetch_close_prices(bt_conn, trading_day)
            simulator.mark_to_market(trading_day, close_prices)

            # Step 4: 翌日用シグナル生成（bt_conn の positions を読んで SELL 判定）
            generate_signals(bt_conn, target_date=trading_day)

            # Step 5: ポートフォリオ構築（Phase 5 モジュール使用）
            buy_signals, sell_signals = _read_day_signals(bt_conn, trading_day)
            regime = _fetch_regime(bt_conn, trading_day)
            multiplier = calc_regime_multiplier(regime)
            prior_pv = simulator.history[-1].portfolio_value if simulator.history else initial_cash
            available_cash = simulator.cash * multiplier

            candidates = select_candidates(buy_signals, max_positions)
            candidates = apply_sector_cap(
                candidates, sector_map, prior_pv, simulator.positions, open_prices
            )

            if allocation_method == "equal":
                weights = calc_equal_weights(candidates)
            elif allocation_method == "score":
                weights = calc_score_weights(candidates)
            else:
                weights = {}  # risk_based は weights 不使用

            sized = calc_position_sizes(
                weights=weights,
                candidates=candidates,
                portfolio_value=prior_pv,
                available_cash=available_cash,
                current_positions=simulator.positions,
                open_prices=open_prices,
                allocation_method=allocation_method,
                risk_pct=risk_pct,
                stop_loss_pct=stop_loss_pct,
                max_position_pct=max_position_pct,
                max_utilization=max_utilization,
            )

            signals_prev = [
                {"code": code, "side": "buy", "shares": shares}
                for code, shares in sized.items()
                if shares > 0
            ] + [{"code": s["code"], "side": "sell"} for s in sell_signals]
    finally:
        bt_conn.close()
    metrics = calc_metrics(simulator.history, simulator.trades)
    logger.info(
        "run_backtest: 完了 CAGR=%.2f%% Sharpe=%.3f MaxDD=%.2f%% Trades=%d",
        metrics.cagr * 100, metrics.sharpe_ratio,
        metrics.max_drawdown * 100, metrics.total_trades,
    )
    return BacktestResult(
        history=simulator.history,
        trades=simulator.trades,
        metrics=metrics,
    )
