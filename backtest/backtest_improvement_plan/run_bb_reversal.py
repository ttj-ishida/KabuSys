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

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import PortfolioSimulator
from kabusys.data.calendar_management import get_trading_days
from kabusys.portfolio import calc_equal_weights, calc_position_sizes, select_candidates

logger = logging.getLogger(__name__)

SCENARIOS: list[dict] = [
    {"id": "BB1_base",          "period": 20, "sigma": 2.0, "regime_filter": False},
    {"id": "BB2_tight",         "period": 20, "sigma": 1.5, "regime_filter": False},
    {"id": "BB3_wide",          "period": 20, "sigma": 2.5, "regime_filter": False},
    {"id": "BB4_base_regime",   "period": 20, "sigma": 2.0, "regime_filter": True},
    {"id": "BB5_tight_regime",  "period": 20, "sigma": 1.5, "regime_filter": True},
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

    TOPIX または市場ブレッドスコアが弱気レジームを示す場合 True を返す。
    regime_score テーブルが存在しない場合は False（フィルタなし）を返す。

    Args:
        conn: DuckDB 接続
        trading_day: 判定対象日

    Returns:
        True = 買いブロック, False = 買い許可
    """
    try:
        result = conn.execute(
            """
            SELECT regime
            FROM regime_score
            WHERE date = ?
            LIMIT 1
            """,
            [trading_day],
        ).fetchone()
        if result is None:
            return False
        regime = result[0]
        # "bear" または "down" を含む場合はブロック
        return str(regime).lower() in ("bear", "down", "bearish")
    except Exception:
        return False
