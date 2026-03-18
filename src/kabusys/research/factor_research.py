"""
ファクター計算モジュール

StrategyModel.md Section 3 に基づき、以下の定量ファクターを計算する。

ファクター群:
  - Momentum  : 1M/3M/6M リターン、200日移動平均乖離率
  - Value     : PBR、PER、配当利回り（fundamentals テーブルから取得）
  - Volatility: 20日 ATR（Average True Range）
  - Liquidity : 20日平均売買代金、出来高変化率

設計方針:
  - DuckDB 接続を受け取り SQL + Python で計算する（外部 API 呼び出しなし）
  - 全関数は prices_daily / raw_financials テーブルのみを参照する
    （本番口座・発注 API には一切アクセスしない）
  - 結果は (date, code) をキーとする dict のリストで返す
  - Zスコア正規化ユーティリティを提供する
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_MOMENTUM_SHORT_DAYS = 21    # 約1ヶ月（営業日）
_MOMENTUM_MID_DAYS = 63      # 約3ヶ月（営業日）
_MOMENTUM_LONG_DAYS = 126    # 約6ヶ月（営業日）
_MA_LONG_DAYS = 200          # 長期移動平均
_ATR_DAYS = 20               # ATR 計算期間
_VOLUME_DAYS = 20            # 出来高移動平均期間


# ---------------------------------------------------------------------------
# モメンタム ファクター
# ---------------------------------------------------------------------------


def calc_momentum(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """モメンタムファクターを計算する。

    対象日を基準に、各銘柄の以下のリターンを計算する。
      - mom_1m : 約1ヶ月前終値に対するリターン
      - mom_3m : 約3ヶ月前終値に対するリターン
      - mom_6m : 約6ヶ月前終値に対するリターン
      - ma200_dev: 200日移動平均に対する乖離率（(close - MA200) / MA200）

    データ不足（過去データが少ない）銘柄は None を返す。

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "mom_1m": float|None, ...}, ...] のリスト。
    """
    rows = conn.execute(
        f"""
        WITH base AS (
            SELECT
                code,
                close,
                date,
                LAG(close, {_MOMENTUM_SHORT_DAYS}) OVER (PARTITION BY code ORDER BY date) AS close_1m_ago,
                LAG(close, {_MOMENTUM_MID_DAYS}) OVER (PARTITION BY code ORDER BY date) AS close_3m_ago,
                LAG(close, {_MOMENTUM_LONG_DAYS}) OVER (PARTITION BY code ORDER BY date) AS close_6m_ago,
                AVG(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_MA_LONG_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS ma200
            FROM prices_daily
            WHERE date <= ?
        )
        SELECT
            date,
            code,
            CASE WHEN close_1m_ago > 0
                 THEN (close - close_1m_ago) / close_1m_ago END AS mom_1m,
            CASE WHEN close_3m_ago > 0
                 THEN (close - close_3m_ago) / close_3m_ago END AS mom_3m,
            CASE WHEN close_6m_ago > 0
                 THEN (close - close_6m_ago) / close_6m_ago END AS mom_6m,
            CASE WHEN ma200 > 0
                 THEN (close - ma200) / ma200 END AS ma200_dev
        FROM base
        WHERE date = ?
        ORDER BY code
        """,
        [target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "mom_1m", "mom_3m", "mom_6m", "ma200_dev"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.info("calc_momentum: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# ボラティリティ ファクター
# ---------------------------------------------------------------------------


def calc_volatility(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """ボラティリティ・流動性ファクターを計算する。

    各銘柄について以下を計算する。
      - atr_20       : 20日 ATR（Average True Range）の単純平均
      - atr_pct      : ATR / close（相対 ATR、銘柄間比較用）
      - avg_turnover : 20日平均売買代金
      - volume_ratio : 当日出来高 / 20日平均出来高

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "atr_20": float|None, ...}, ...] のリスト。
    """
    rows = conn.execute(
        f"""
        WITH tr AS (
            SELECT
                date,
                code,
                close,
                volume,
                turnover,
                GREATEST(
                    high - low,
                    COALESCE(ABS(high - LAG(close) OVER (PARTITION BY code ORDER BY date)), 0),
                    COALESCE(ABS(low  - LAG(close) OVER (PARTITION BY code ORDER BY date)), 0)
                ) AS true_range
            FROM prices_daily
            WHERE date <= ?
        ),
        agg AS (
            SELECT
                date,
                code,
                close,
                AVG(true_range) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_ATR_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS atr_20,
                AVG(turnover) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_VOLUME_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS avg_turnover,
                AVG(volume) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_VOLUME_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS avg_volume,
                volume AS curr_volume
            FROM tr
        )
        SELECT
            date,
            code,
            atr_20,
            CASE WHEN close > 0 THEN atr_20 / close END AS atr_pct,
            avg_turnover,
            CASE WHEN avg_volume > 0 THEN curr_volume / avg_volume END AS volume_ratio
        FROM agg
        WHERE date = ?
        ORDER BY code
        """,
        [target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "atr_20", "atr_pct", "avg_turnover", "volume_ratio"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.info("calc_volatility: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# バリュー ファクター
# ---------------------------------------------------------------------------


def calc_value(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """バリューファクターを計算する。

    raw_financials テーブルから target_date 以前の最新財務データを取得し、
    prices_daily の株価と組み合わせて以下を計算する。
      - pbr : 株価 / BPS（= close / (net_income / eps * pbr_proxy）※ EPS ベース簡易計算）
      - per : 株価 / EPS
      - roe : ROE（raw_financials から直接取得）

    EPS が 0 または欠損の場合は per = None を返す。

    Args:
        conn:        DuckDB 接続。prices_daily / raw_financials テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "per": float|None, "roe": float|None}, ...] のリスト。
    """
    rows = conn.execute(
        """
        WITH latest_fin AS (
            -- target_date 以前の最新財務レコードを銘柄ごとに1件取得（DuckDB 互換: ROW_NUMBER 使用）
            SELECT code, eps, roe
            FROM (
                SELECT code, eps, roe,
                       ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) AS rn
                FROM raw_financials
                WHERE report_date <= ?
            ) t
            WHERE rn = 1
        ),
        price_on_date AS (
            SELECT code, close
            FROM prices_daily
            WHERE date = ?
        )
        SELECT
            ? AS date,
            p.code,
            CASE WHEN f.eps IS NOT NULL AND f.eps <> 0
                 THEN p.close / f.eps END AS per,
            f.roe
        FROM price_on_date p
        LEFT JOIN latest_fin f ON p.code = f.code
        ORDER BY p.code
        """,
        [target_date, target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "per", "roe"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.info("calc_value: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# Zスコア正規化
# ---------------------------------------------------------------------------


def zscore_normalize(
    records: list[dict[str, Any]],
    columns: list[str],
) -> list[dict[str, Any]]:
    """指定カラムを Zスコア正規化する（クロスセクション）。

    各カラムについて mean/std をクロスセクション（全銘柄）で計算し、
    (value - mean) / std に変換する。

    std が 0 またはレコードが 1 件以下の場合は元の値を維持する。
    None 値はスキップして計算し、正規化後も None を返す。

    Args:
        records: ファクター計算関数の戻り値リスト。
        columns: 正規化対象のカラム名リスト。

    Returns:
        正規化済みのレコードリスト（元のリストを変更しない）。
    """
    import copy
    result = copy.deepcopy(records)

    for col in columns:
        values = [r[col] for r in result if r.get(col) is not None]
        if len(values) <= 1:
            continue
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        if std == 0:
            continue
        for r in result:
            if r.get(col) is not None:
                r[col] = (r[col] - mean) / std

    return result
