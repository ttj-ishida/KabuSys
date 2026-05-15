"""
ファクター計算モジュール

StrategyModel.md Section 3 に基づき、以下の定量ファクターを計算する。

ファクター群:
  - Momentum  : 1M/3M/6M リターン、200日移動平均乖離率
  - Value     : PER、ROE（raw_financials テーブルから取得）
  - Volatility: 20日 ATR（Average True Range）
  - Liquidity : 20日平均売買代金、出来高変化率

設計方針:
  - DuckDB 接続を受け取り SQL + Python で計算する（外部 API 呼び出しなし）
  - 全関数は prices_daily / raw_financials テーブルのみを参照する
    （本番口座・発注 API には一切アクセスしない）
  - 結果は (date, code) をキーとする dict のリストで返す
  - Zスコア正規化ユーティリティは kabusys.data.stats から提供する
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_MOMENTUM_SHORT_DAYS = 21  # 約1ヶ月（営業日）
_MOMENTUM_MID_DAYS = 63  # 約3ヶ月（営業日）
_MOMENTUM_LONG_DAYS = 126  # 約6ヶ月（営業日）
_MA_LONG_DAYS = 200  # 長期移動平均
_ATR_DAYS = 20  # ATR 計算期間
_VOLUME_DAYS = 20  # 出来高移動平均期間

# スキャン範囲バッファ（営業日×2 カレンダー日で週末・祝日を吸収）
_MOMENTUM_SCAN_DAYS = _MA_LONG_DAYS * 2  # 400 calendar days
_VOLATILITY_SCAN_DAYS = _ATR_DAYS * 3  # 60 calendar days


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
                   ウィンドウ内データが 200 行未満の場合は None を返す。

    データ不足（過去データが少ない）銘柄は None を返す。

    Note:
        horizons は営業日ベース（連続レコード数）であり、カレンダー日ではない。

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "mom_1m": float|None, ...}, ...] のリスト。
    """
    start_date = target_date - timedelta(days=_MOMENTUM_SCAN_DAYS)

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
                ) AS ma200,
                COUNT(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_MA_LONG_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS cnt_200
            FROM prices_daily
            WHERE date BETWEEN ? AND ?
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
            CASE WHEN ma200 > 0 AND cnt_200 >= {_MA_LONG_DAYS}
                 THEN (close - ma200) / ma200 END AS ma200_dev
        FROM base
        WHERE date = (SELECT MAX(date) FROM prices_daily WHERE date <= ?)
        ORDER BY code
        """,
        [start_date, target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "mom_1m", "mom_3m", "mom_6m", "ma200_dev"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.debug("calc_momentum: %d 銘柄 date=%s", len(result), target_date)
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
                       ウィンドウ内データが 20 行未満の場合は None を返す。
      - atr_pct      : ATR / close（相対 ATR、銘柄間比較用）
      - avg_turnover : 20日平均売買代金（部分窓でも算出）
      - volume_ratio : 当日出来高 / 20日平均出来高

    Note:
        horizons は営業日ベース（連続レコード数）であり、カレンダー日ではない。

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "atr_20": float|None, ...}, ...] のリスト。
    """
    start_date = target_date - timedelta(days=_VOLATILITY_SCAN_DAYS)

    rows = conn.execute(
        f"""
        WITH base AS (
            -- prev_close を事前計算することで true_range の NULL 伝播を正確に制御する
            SELECT
                date, code, high, low, close, volume, turnover,
                LAG(close) OVER (PARTITION BY code ORDER BY date) AS prev_close
            FROM prices_daily
            WHERE date BETWEEN ? AND ?
        ),
        tr AS (
            SELECT
                date, code, close, volume, turnover,
                -- high/low/prev_close のいずれかが NULL なら true_range も NULL とする
                -- （COALESCE で 0 に潰すと cnt_atr が過大評価されるため）
                CASE
                    WHEN high IS NULL OR low IS NULL OR prev_close IS NULL
                        THEN NULL
                    ELSE GREATEST(
                        high - low,
                        ABS(high - prev_close),
                        ABS(low  - prev_close)
                    )
                END AS true_range
            FROM base
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
                COUNT(true_range) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {_ATR_DAYS - 1} PRECEDING AND CURRENT ROW
                ) AS cnt_atr,
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
            CASE WHEN cnt_atr >= {_ATR_DAYS} THEN atr_20 END AS atr_20,
            CASE WHEN close > 0 AND cnt_atr >= {_ATR_DAYS} THEN atr_20 / close END AS atr_pct,
            avg_turnover,
            CASE WHEN avg_volume > 0 THEN curr_volume / avg_volume END AS volume_ratio
        FROM agg
        WHERE date = (SELECT MAX(date) FROM prices_daily WHERE date <= ?)
        ORDER BY code
        """,
        [start_date, target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "atr_20", "atr_pct", "avg_turnover", "volume_ratio"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.debug("calc_volatility: %d 銘柄 date=%s", len(result), target_date)
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
      - per       : 株価 / EPS（EPS が 0 または欠損の場合は None）
      - roe       : ROE（raw_financials から直接取得）
      - pbr       : 株価 / BPS（BPS が 0 または欠損の場合は None）
      - div_yield : 直近12ヶ月の配当合計 / 株価 × 100（配当なしの場合は None）

    Args:
        conn:        DuckDB 接続。prices_daily / raw_financials / dividends テーブルを参照。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "per": float|None, "roe": float|None,
          "pbr": float|None, "div_yield": float|None}, ...] のリスト。
    """
    rows = conn.execute(
        """
        WITH latest_fin AS (
            SELECT code, eps, roe, bps
            FROM (
                SELECT code, eps, roe, bps,
                       ROW_NUMBER() OVER (
                           PARTITION BY code ORDER BY report_date DESC, fetched_at DESC
                       ) AS rn
                FROM raw_financials
                WHERE report_date <= ?
            ) t
            WHERE rn = 1
        ),
        price_on_date AS (
            SELECT code, close
            FROM prices_daily
            WHERE date = (SELECT MAX(date) FROM prices_daily WHERE date <= ?)
        ),
        annual_div AS (
            SELECT code, SUM(div_rate) AS annual_div
            FROM dividends
            WHERE code IN (SELECT code FROM price_on_date)
              AND ex_date BETWEEN (CAST(? AS DATE) - INTERVAL 1 YEAR) AND ?
            GROUP BY code
        )
        SELECT
            ? AS date,
            p.code,
            CASE WHEN f.eps IS NOT NULL AND f.eps <> 0
                 THEN p.close / f.eps END AS per,
            f.roe,
            CASE WHEN f.bps IS NOT NULL AND f.bps > 0
                 THEN p.close / f.bps END AS pbr,
            CASE WHEN d.annual_div IS NOT NULL AND p.close > 0
                 THEN (d.annual_div / p.close) * 100 END AS div_yield
        FROM price_on_date p
        LEFT JOIN latest_fin f ON p.code = f.code
        LEFT JOIN annual_div d ON p.code = d.code
        ORDER BY p.code
        """,
        [target_date, target_date, target_date, target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "per", "roe", "pbr", "div_yield"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.debug("calc_value: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# TOPIX 相対強度ファクター
# ---------------------------------------------------------------------------


def calc_topix_relative(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """TOPIX 対比の相対モメンタムを計算する。

    各銘柄の 21 日・63 日リターンから同期間の TOPIX リターンを差し引く。
    topix_daily にデータが存在しない場合は空リストを返す。

    Args:
        conn:        DuckDB 接続。prices_daily / topix_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"date": date, "code": str, "topix_rel_20": float|None, "topix_rel_60": float|None}]
    """
    start_date = target_date - timedelta(days=_MOMENTUM_SCAN_DAYS)

    topix_row = conn.execute(
        f"""
        WITH topix_data AS (
            SELECT date, close,
                   LAG(close, {_MOMENTUM_SHORT_DAYS}) OVER (ORDER BY date) AS close_short_ago,
                   LAG(close, {_MOMENTUM_MID_DAYS})   OVER (ORDER BY date) AS close_mid_ago
            FROM topix_daily
            WHERE date BETWEEN ? AND ?
        )
        SELECT
            CASE WHEN close_short_ago > 0
                 THEN (close - close_short_ago) / close_short_ago END AS ret_short,
            CASE WHEN close_mid_ago > 0
                 THEN (close - close_mid_ago) / close_mid_ago END AS ret_mid
        FROM topix_data
        WHERE date = (SELECT MAX(date) FROM topix_daily WHERE date <= ?)
        """,
        [start_date, target_date, target_date],
    ).fetchone()

    if topix_row is None:
        logger.warning("calc_topix_relative: TOPIX データ不足 date=%s", target_date)
        return []

    topix_ret_short = float(topix_row[0]) if topix_row[0] is not None else None
    topix_ret_mid = float(topix_row[1]) if topix_row[1] is not None else None
    if topix_ret_short is None and topix_ret_mid is None:
        logger.warning(
            "calc_topix_relative: TOPIX LAG ウィンドウ不足（データは存在するがリターン計算不可）date=%s",
            target_date,
        )
        return []

    rows = conn.execute(
        f"""
        WITH stock_data AS (
            SELECT code, date, close,
                   LAG(close, {_MOMENTUM_SHORT_DAYS}) OVER (PARTITION BY code ORDER BY date)
                       AS close_short_ago,
                   LAG(close, {_MOMENTUM_MID_DAYS})   OVER (PARTITION BY code ORDER BY date)
                       AS close_mid_ago
            FROM prices_daily
            WHERE date BETWEEN ? AND ?
        )
        SELECT date, code,
               CASE WHEN close_short_ago > 0
                    THEN (close - close_short_ago) / close_short_ago END AS ret_short,
               CASE WHEN close_mid_ago > 0
                    THEN (close - close_mid_ago) / close_mid_ago END AS ret_mid
        FROM stock_data
        WHERE date = (
            SELECT MAX(date) FROM prices_daily WHERE date <= ?
        )
        ORDER BY code
        """,
        [start_date, target_date, target_date],
    ).fetchall()

    result = []
    for _row_date, code, ret_short, ret_mid in rows:
        stock_ret_short = float(ret_short) if ret_short is not None else None
        stock_ret_mid = float(ret_mid) if ret_mid is not None else None
        topix_rel_20 = (
            stock_ret_short - topix_ret_short
            if stock_ret_short is not None and topix_ret_short is not None
            else None
        )
        topix_rel_60 = (
            stock_ret_mid - topix_ret_mid
            if stock_ret_mid is not None and topix_ret_mid is not None
            else None
        )
        result.append(
            {
                "date": target_date,
                "code": code,
                "topix_rel_20": topix_rel_20,
                "topix_rel_60": topix_rel_60,
            }
        )

    logger.debug("calc_topix_relative: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# 財務品質ファクター
# ---------------------------------------------------------------------------


def calc_quality(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """財務品質指標を計算する。

    raw_financials の年次（FY）データから以下を計算する。
      - op_margin       : 営業利益率（operating_profit / revenue）
      - rev_growth_yoy  : 売上 YoY 成長率（最新 FY / 直前 FY - 1）
      - profit_growth_yoy: 営業利益 YoY 成長率（最新 FY / 直前 FY - 1）

    period_type が 'FYResult%' に一致する通期実績レコードのみを対象とする
    （FYForecastRevision 等の予想・修正系は除外）。
    年次データが 1 件のみの場合は成長率が None になる。

    Args:
        conn:        DuckDB 接続。raw_financials テーブルを参照する。
        target_date: 計算基準日（report_date <= target_date のデータのみ使用）。

    Returns:
        [{"date": date, "code": str, "op_margin": float|None,
          "rev_growth_yoy": float|None, "profit_growth_yoy": float|None}]
    """
    rows = conn.execute(
        """
        WITH fy_ranked AS (
            SELECT code, report_date, revenue, operating_profit,
                   ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC, fetched_at DESC) AS rn
            FROM raw_financials
            WHERE report_date <= ?
              AND period_type = 'FY'
        ),
        latest_fy AS (SELECT * FROM fy_ranked WHERE rn = 1),
        prior_fy  AS (SELECT * FROM fy_ranked WHERE rn = 2)
        SELECT
            ? AS date,
            l.code,
            CASE WHEN l.revenue > 0 AND l.operating_profit IS NOT NULL
                 THEN l.operating_profit / l.revenue END AS op_margin,
            CASE WHEN p.revenue IS NOT NULL AND p.revenue <> 0
                      AND l.revenue IS NOT NULL
                 THEN (l.revenue - p.revenue) / ABS(p.revenue) END AS rev_growth_yoy,
            CASE WHEN p.operating_profit IS NOT NULL AND p.operating_profit <> 0
                      AND l.operating_profit IS NOT NULL
                 THEN (l.operating_profit - p.operating_profit) / ABS(p.operating_profit)
                 END AS profit_growth_yoy
        FROM latest_fy l
        LEFT JOIN prior_fy p ON l.code = p.code
        ORDER BY l.code
        """,
        [target_date, target_date],
    ).fetchall()

    cols = ["date", "code", "op_margin", "rev_growth_yoy", "profit_growth_yoy"]
    result = [dict(zip(cols, r)) for r in rows]
    logger.debug("calc_quality: %d 銘柄 date=%s", len(result), target_date)
    return result


# ---------------------------------------------------------------------------
# RSI ファクター
# ---------------------------------------------------------------------------

_RSI_PERIOD = 14  # Wilder's RSI 期間
_RSI_SCAN_DAYS = (_RSI_PERIOD + 1) * 3  # データスキャン範囲（カレンダー日）


def calc_rsi(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> list[dict[str, Any]]:
    """RSI(14) を計算する。

    Wilder の平滑移動平均（初期値は単純平均）で計算する。
    target_date 以前の最新 14+1 件の終値を使用するため、ルックアヘッドバイアスはない。
    データ件数が 15 件未満の銘柄は rsi_14=None を返す。

    Args:
        conn:        DuckDB 接続。prices_daily テーブルを参照する。
        target_date: 計算基準日。

    Returns:
        [{"code": str, "rsi_14": float | None}, ...] のリスト。
    """
    scan_from = target_date - timedelta(days=_RSI_SCAN_DAYS)
    rows = conn.execute(
        """
        WITH price_window AS (
            SELECT code, date,
                CAST(close AS DOUBLE) AS close,
                ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
            FROM prices_daily
            WHERE date <= ? AND date >= ?
              AND close IS NOT NULL
        ),
        recent AS (
            SELECT code, date, close
            FROM price_window
            WHERE rn <= ?
        ),
        changes AS (
            SELECT code, date,
                close - LAG(close) OVER (PARTITION BY code ORDER BY date) AS chg
            FROM recent
        ),
        gains_losses AS (
            SELECT code,
                GREATEST(chg, 0)  AS gain,
                GREATEST(-chg, 0) AS loss
            FROM changes
            WHERE chg IS NOT NULL
        ),
        counts AS (
            SELECT code, COUNT(*) AS n FROM gains_losses GROUP BY code
        ),
        avg_gl AS (
            SELECT g.code,
                AVG(g.gain) AS avg_gain,
                AVG(g.loss) AS avg_loss
            FROM gains_losses g
            INNER JOIN counts c ON g.code = c.code
            WHERE c.n >= ?
            GROUP BY g.code
        )
        SELECT code,
            CASE
                WHEN avg_gain = 0 AND avg_loss = 0 THEN NULL
                WHEN avg_loss = 0 THEN 100.0
                ELSE 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
            END AS rsi_14
        FROM avg_gl
        ORDER BY code
        """,
        [target_date, scan_from, _RSI_PERIOD + 1, _RSI_PERIOD],
    ).fetchall()

    result = [{"code": code, "rsi_14": rsi} for code, rsi in rows]
    logger.debug("calc_rsi: %d 銘柄 date=%s", len(result), target_date)
    return result
