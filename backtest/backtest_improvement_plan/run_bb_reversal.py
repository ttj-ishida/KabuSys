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
) -> list[str]:
    """BB ロワーバンド割れの銘柄コードリストを返す。

    Args:
        bb_rows: [(code, close, lower_band, middle_band), ...]

    Returns:
        close < lower_band の銘柄コードリスト
    """
    return [code for code, close, lower_band, _mid in bb_rows if close < lower_band]


def _generate_sell_signals(
    bb_rows: list[tuple[str, float, float, float]],
    holdings: set[str],
) -> list[str]:
    """ミドルバンド以上に回復した保有銘柄コードリストを返す。

    Args:
        bb_rows: [(code, close, lower_band, middle_band), ...]
        holdings: 現在保有中の銘柄コードセット

    Returns:
        close >= middle_band かつ holdings に含まれる銘柄コードリスト
    """
    bb_map = {code: (close, middle_band) for code, close, _lb, middle_band in bb_rows}
    result: list[str] = []
    for code in holdings:
        if code in bb_map:
            close, middle_band = bb_map[code]
            if close >= middle_band:
                result.append(code)
    return result


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
