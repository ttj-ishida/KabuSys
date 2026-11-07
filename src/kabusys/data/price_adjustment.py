"""株式分割・併合の補正（後方補正）— Issue #424。

``prices_daily`` は ``raw_prices`` を分割・併合で後方補正した系列とする。

銘柄ごとに日付 d の補正倍率を ``M(d) = Π_{t > d} f(t)`` とする
（f = ``raw_prices.adj_factor``。NULL・0 以下は 1 とみなす）。

- open / high / low / close = raw × M(d)
- volume = round(raw / M(d))
- turnover = raw（売買代金は補正しない）

最新日は M = 1 なので直近の株価は実際の株価と一致する。M(d) はその時点の DB に
ある係数だけから計算するため、後日の分割で過去の絶対水準は変わる（既知のトレードオフ）。

計算はすべて DuckDB のウィンドウ関数で行う（Python で行ループしない）。
"""

from __future__ import annotations

import logging
from datetime import date

import duckdb

logger = logging.getLogger(__name__)

# raw_prices → prices_daily の品質フィルタ（pipeline.sync_raw_prices_to_prices_daily と共通）
QUALITY_FILTER = """
    open IS NOT NULL AND open > 0
    AND high IS NOT NULL AND high > 0
    AND low IS NOT NULL AND low > 0
    AND close IS NOT NULL AND close > 0
    AND volume IS NOT NULL
    AND low <= high
"""

# 係数のスナップ許容誤差。J-Quants の AdjFactor は小数 6 桁（1:3 → 0.333333）のため、
# 整数比に十分近い値は厳密な比率（1/3 や 10）として扱う。
SNAP_TOLERANCE = 1e-5

# 調整係数として有効な値（NULL・0 以下は 1 とみなし、整数比に近い値はスナップする）。
# snap_factor() と同じ規則。
_RAW_F = "CAST(adj_factor AS DOUBLE)"
_FACTOR_EXPR = f"""
    CASE
        WHEN adj_factor IS NULL OR adj_factor <= 0 THEN 1.0
        WHEN {_RAW_F} < 1 AND ABS({_RAW_F} - 1.0 / ROUND(1.0 / {_RAW_F}))
             < {SNAP_TOLERANCE} THEN 1.0 / ROUND(1.0 / {_RAW_F})
        WHEN {_RAW_F} > 1 AND ABS({_RAW_F} - ROUND({_RAW_F})) < {SNAP_TOLERANCE}
             THEN ROUND({_RAW_F})
        ELSE {_RAW_F}
    END
"""


def snap_factor(f: float | None) -> float:
    """調整係数を正規化する（_FACTOR_EXPR と同じ規則。手動保有の換算で使う）。

    NULL・0 以下 → 1。1 未満で 1/n に近い → 1/n。1 より大きく整数 n に近い → n。
    """
    if f is None:
        return 1.0
    f = float(f)
    if f <= 0:
        return 1.0
    if f < 1:
        n = round(1.0 / f)
        if abs(f - 1.0 / n) < SNAP_TOLERANCE:
            return 1.0 / n
    elif f > 1:
        n = round(f)
        if abs(f - n) < SNAP_TOLERANCE:
            return float(n)
    return f


# 1 以外の有効な係数を持つ行
NONTRIVIAL_FACTOR_PRED = "adj_factor IS NOT NULL AND adj_factor > 0 AND adj_factor <> 1"


def adjusted_select_sql(source_where: str, output_where: str) -> str:
    """補正済みの prices_daily 行を返す SELECT 文を組み立てる。

    Args:
        source_where: M(d) の計算に使う raw_prices 行の条件。各銘柄について、
            出力する日付より後の行がすべて含まれていること。
        output_where: 出力する行の条件（品質フィルタとは別に AND で適用する）。
    """
    return f"""
        WITH src AS (
            SELECT date, code, open, high, low, close, volume, turnover,
                   {_FACTOR_EXPR} AS f
            FROM raw_prices
            WHERE {source_where}
        ),
        m AS (
            SELECT *,
                   COALESCE(
                       PRODUCT(f) OVER (
                           PARTITION BY code ORDER BY date
                           ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING
                       ),
                       1.0
                   ) AS mult
            FROM src
        )
        SELECT date, code,
               CAST(open AS DOUBLE) * mult  AS open,
               CAST(high AS DOUBLE) * mult  AS high,
               CAST(low AS DOUBLE) * mult   AS low,
               CAST(close AS DOUBLE) * mult AS close,
               CAST(ROUND(volume / mult) AS BIGINT) AS volume,
               turnover
        FROM m
        WHERE ({QUALITY_FILTER}) AND ({output_where})
    """


_UPSERT_PREFIX = """
    INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover)
"""

_UPSERT_SUFFIX = """
    ON CONFLICT (date, code) DO UPDATE SET
        open = excluded.open,
        high = excluded.high,
        low = excluded.low,
        close = excluded.close,
        volume = excluded.volume,
        turnover = excluded.turnover
"""


def upsert_adjusted_range(conn: duckdb.DuckDBPyConnection, date_from: date, date_to: date) -> None:
    """[date_from, date_to] の raw_prices 行を補正して prices_daily に upsert する。

    M(d) には date_from 以降の raw_prices 行（date_to より後も含む）の係数を使う。
    トランザクションは呼び出し元が管理する。
    """
    sql = adjusted_select_sql("date >= ?", "date <= ?")
    conn.execute(_UPSERT_PREFIX + sql + _UPSERT_SUFFIX, [date_from, date_to])


def codes_with_factors(
    conn: duckdb.DuckDBPyConnection,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[str]:
    """1 以外の adj_factor を持つ銘柄（期間指定可）を返す。"""
    where = [NONTRIVIAL_FACTOR_PRED]
    params: list[date] = []
    if date_from is not None:
        where.append("date >= ?")
        params.append(date_from)
    if date_to is not None:
        where.append("date <= ?")
        params.append(date_to)
    rows = conn.execute(
        f"SELECT DISTINCT code FROM raw_prices WHERE {' AND '.join(where)} ORDER BY code",
        params,
    ).fetchall()
    return [str(r[0]) for r in rows]


def rebuild_codes(conn: duckdb.DuckDBPyConnection, codes: list[str]) -> int:
    """指定銘柄の prices_daily を raw_prices の全期間から作り直す（トランザクションは呼び出し元）。

    - 品質フィルタを通る行は補正済みの値で upsert する。
    - raw_prices にあって品質フィルタを通らない行が prices_daily に残っていれば削除する。
    - raw_prices に対応行がない prices_daily 行は触らない。

    Returns:
        書き込んだ（upsert した）prices_daily の行数。
    """
    if not codes:
        return 0
    conn.execute("CREATE OR REPLACE TEMP TABLE _adj_codes (code VARCHAR PRIMARY KEY)")
    try:
        conn.execute(
            "INSERT INTO _adj_codes SELECT DISTINCT unnest(?::VARCHAR[])",
            [list(codes)],
        )
        code_pred = "code IN (SELECT code FROM _adj_codes)"
        conn.execute(
            f"""
            DELETE FROM prices_daily
            WHERE {code_pred}
              AND (date, code) IN (
                  SELECT date, code FROM raw_prices
                  WHERE {code_pred} AND NOT COALESCE(({QUALITY_FILTER}), FALSE)
              )
            """
        )
        conn.execute(
            _UPSERT_PREFIX + adjusted_select_sql(code_pred, "TRUE") + _UPSERT_SUFFIX,
        )
        row = conn.execute(
            f"SELECT COUNT(*) FROM raw_prices WHERE {code_pred} AND ({QUALITY_FILTER})"
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.execute("DROP TABLE IF EXISTS _adj_codes")


def rebuild_adjusted_prices(conn: duckdb.DuckDBPyConnection, codes: list[str] | None = None) -> int:
    """指定銘柄の prices_daily を補正済みの値で作り直す（冪等）。

    Args:
        conn:  DuckDB 接続（書き込み可）。
        codes: 対象銘柄。None のときは 1 以外の adj_factor を持つ全銘柄。

    Returns:
        書き込んだ prices_daily の行数。
    """
    targets = codes_with_factors(conn) if codes is None else list(dict.fromkeys(codes))
    if not targets:
        logger.info("rebuild_adjusted_prices: 対象銘柄なし")
        return 0
    conn.execute("BEGIN")
    try:
        n = rebuild_codes(conn, targets)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    logger.info("rebuild_adjusted_prices: %d 銘柄 / %d 行を作り直しました", len(targets), n)
    return n
