"""
市場 breadth（幅）指標の計算と保存モジュール

prices_daily テーブルから騰落レシオ・25日MA上銘柄比率・新高値新安値比率を
計算し、market_breadth テーブルへ日次1行として保存する。

冪等: 同日を再実行しても上書きせず 0 を返す。
"""

from __future__ import annotations

import logging
from datetime import date

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_MIN_TRADING_DAYS: int = 25
_MIN_STOCKS: int = 10
_BREADTH_STOP_THRESHOLD: float = 0.35
_ADV_DECLINE_ZERO_DECLINES: float = 200.0


# ---------------------------------------------------------------------------
# 内部計算関数
# ---------------------------------------------------------------------------


def _calc_adv_decline_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float:
    """直近25営業日の騰落レシオを計算する。

    前日比較のため 26 日分（LIMIT 26）を取得し LAG で差分を計算。
    上位 25 日分のみ集計することで 26 日目が prev_close の計算に使われる。
    declines=0 の場合は _ADV_DECLINE_ZERO_DECLINES を返す。
    """
    row = conn.execute(
        """
        WITH dates_desc AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 26
        ),
        with_lag AS (
            SELECT
                p.date,
                p.code,
                p.close,
                LAG(p.close) OVER (PARTITION BY p.code ORDER BY p.date) AS prev_close
            FROM prices_daily p
            WHERE p.date IN (SELECT date FROM dates_desc)
        ),
        top25 AS (
            SELECT date FROM dates_desc ORDER BY date DESC LIMIT 25
        )
        SELECT
            COALESCE(SUM(CASE WHEN wl.close > wl.prev_close THEN 1 ELSE 0 END), 0) AS advances,
            COALESCE(SUM(CASE WHEN wl.close < wl.prev_close THEN 1 ELSE 0 END), 0) AS declines
        FROM with_lag wl
        INNER JOIN top25 t ON wl.date = t.date
        WHERE wl.prev_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None:
        return _ADV_DECLINE_ZERO_DECLINES

    advances, declines = row[0], row[1]
    if declines == 0:
        return _ADV_DECLINE_ZERO_DECLINES
    return advances / declines * 100.0


def _calc_ma25_above_pct(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float | None:
    """25日移動平均上銘柄比率を計算する。

    各銘柄の直近25日終値の単純平均（ma25）と最新終値を比較し、
    close > ma25 の銘柄数 / 全銘柄数を返す。
    全25日分のデータがある銘柄のみ対象とする。
    計算対象銘柄が 0 件の場合は None を返す。
    """
    row = conn.execute(
        """
        WITH top25 AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 25
        ),
        latest_date AS (
            SELECT MAX(date) AS d FROM top25
        ),
        stock_stats AS (
            SELECT
                p.code,
                MAX(CASE WHEN p.date = ld.d THEN CAST(p.close AS DOUBLE) END) AS latest_close,
                AVG(CAST(p.close AS DOUBLE)) AS ma25,
                COUNT(DISTINCT p.date) AS days
            FROM prices_daily p
            CROSS JOIN latest_date ld
            WHERE p.date IN (SELECT date FROM top25)
            GROUP BY p.code
        )
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN latest_close > ma25 THEN 1 ELSE 0 END) AS above_ma25
        FROM stock_stats
        WHERE days = 25 AND latest_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None or row[0] == 0:
        return None
    return row[1] / row[0]


def _calc_new_high_low_ratio(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> float | None:
    """52週高値/安値比率を計算する。

    直近250営業日の最高値と等しい銘柄を新高値、最安値と等しい銘柄を新安値とする。
    新安値=0 の場合は None（NULL）を返す。
    high_250 == low_250 の銘柄（250日間ずっと同値）は高値・安値の両方から除外する。
    """
    row = conn.execute(
        """
        WITH window_250 AS (
            SELECT DISTINCT date
            FROM prices_daily
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 250
        ),
        latest_date AS (
            SELECT MAX(date) AS d FROM window_250
        ),
        stock_stats AS (
            SELECT
                p.code,
                MAX(CASE WHEN p.date = ld.d THEN CAST(p.close AS DOUBLE) END) AS latest_close,
                MAX(CAST(p.close AS DOUBLE)) AS high_250,
                MIN(CAST(p.close AS DOUBLE)) AS low_250
            FROM prices_daily p
            CROSS JOIN latest_date ld
            WHERE p.date IN (SELECT date FROM window_250)
            GROUP BY p.code
        )
        SELECT
            SUM(CASE WHEN latest_close = high_250 AND high_250 > low_250 THEN 1 ELSE 0 END) AS new_high,
            SUM(CASE WHEN latest_close = low_250 AND high_250 > low_250 THEN 1 ELSE 0 END) AS new_low
        FROM stock_stats
        WHERE latest_close IS NOT NULL
        """,
        [target_date],
    ).fetchone()

    if row is None:
        return None
    new_high = row[0] or 0
    new_low = row[1] or 0
    if new_low == 0:
        return None
    return new_high / new_low


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def calc_and_save_breadth(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
) -> int:
    """target_date の breadth 指標を prices_daily から計算し market_breadth に保存する。

    Returns:
        1 = 保存成功、0 = 既存スキップまたはデータ不足

    冪等: 同日を再実行しても上書きせず 0 を返す。
    """
    # 冪等チェック（regime_detector と異なり DELETE+INSERT しない。
    # 仕様により同日の再実行は上書きせず 0 を返す）
    existing = conn.execute(
        "SELECT 1 FROM market_breadth WHERE date = ?", [target_date]
    ).fetchone()
    if existing:
        logger.info("calc_and_save_breadth: date=%s は既存スキップ", target_date)
        return 0

    # データ充足確認（取引日数）
    date_count = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM prices_daily WHERE date < ?",
        [target_date],
    ).fetchone()[0]

    if date_count < _MIN_TRADING_DAYS:
        logger.warning(
            "calc_and_save_breadth: データ不足 %d 日（必要: %d） date=%s",
            date_count,
            _MIN_TRADING_DAYS,
            target_date,
        )
        return 0

    # データ充足確認（銘柄数）
    stock_count = conn.execute(
        "SELECT COUNT(DISTINCT code) FROM prices_daily WHERE date < ?",
        [target_date],
    ).fetchone()[0]

    if stock_count < _MIN_STOCKS:
        logger.warning(
            "calc_and_save_breadth: 銘柄数不足 %d 件（必要: %d） date=%s",
            stock_count,
            _MIN_STOCKS,
            target_date,
        )
        return 0

    # 各指標を計算
    adv_decline_ratio = _calc_adv_decline_ratio(conn, target_date)
    ma25_above_pct = _calc_ma25_above_pct(conn, target_date)
    new_high_low_ratio = _calc_new_high_low_ratio(conn, target_date)

    if ma25_above_pct is None:
        logger.warning(
            "calc_and_save_breadth: ma25_above_pct の計算失敗 date=%s", target_date
        )
        return 0

    breadth_stop: bool = ma25_above_pct < _BREADTH_STOP_THRESHOLD

    # DB 書き込み
    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            INSERT INTO market_breadth
                (date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop)
            VALUES (?, ?, ?, ?, ?)
            """,
            [target_date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop],
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("calc_and_save_breadth: ROLLBACK failed: %s", rb_exc)
        raise

    logger.info(
        "calc_and_save_breadth: 完了 date=%s adv_decline=%.1f ma25_pct=%.3f breadth_stop=%s",
        target_date,
        adv_decline_ratio,
        ma25_above_pct,
        breadth_stop,
    )
    return 1
