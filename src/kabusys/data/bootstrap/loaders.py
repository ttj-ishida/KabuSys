from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

# 全ローダーで共用する一時テーブル名（bootstrap は逐次実行なので名前衝突なし）
_TMP = "_bld_src"


def _sql_path(csv_path: Path) -> str:
    """Path を SQL 文字列リテラルとして安全に埋め込む（シングルクォートをエスケープ）。"""
    return str(csv_path).replace("\\", "/").replace("'", "''")


def load_prices(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    bulk: bool = False,
    outer_tx: bool = False,
) -> int:
    """equities/bars/daily CSV → raw_prices & prices_daily

    CSV を TEMP TABLE に一度だけ読み込み（gzip 展開・型変換を1回に抑制）、
    raw と processed の両 INSERT でその TEMP TABLE を参照する。

    bulk=True : 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
    outer_tx  : True のとき BEGIN/COMMIT/ROLLBACK を行わない（呼び出し元がトランザクション管理）。
    """
    path = _sql_path(csv_path)

    conflict_raw = (
        "ON CONFLICT (date, code) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (date, code) DO UPDATE SET "
            "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, "
            "volume=EXCLUDED.volume, turnover=EXCLUDED.turnover, adj_factor=EXCLUDED.adj_factor, "
            "fetched_at=EXCLUDED.fetched_at"
        )
    )
    conflict_proc = (
        "ON CONFLICT (date, code) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (date, code) DO UPDATE SET "
            "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, "
            "volume=EXCLUDED.volume, turnover=EXCLUDED.turnover"
        )
    )

    # CSV を一度だけ展開・型変換してメモリ上の TEMP TABLE に格納
    conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE {_TMP} AS
        SELECT
            TRY_CAST("Date" AS DATE)     AS date,
            TRIM("Code")                 AS code,
            TRY_CAST("O" AS DOUBLE)      AS open,
            TRY_CAST("H" AS DOUBLE)      AS high,
            TRY_CAST("L" AS DOUBLE)      AS low,
            TRY_CAST("C" AS DOUBLE)      AS close,
            TRY_CAST("Vo" AS BIGINT)     AS volume,
            TRY_CAST("Va" AS DOUBLE)     AS turnover,
            TRY_CAST("AdjFactor" AS DOUBLE) AS adj_factor
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE TRY_CAST("Date" AS DATE) IS NOT NULL AND TRIM("Code") != ''
    """)
    try:
        if not outer_tx:
            conn.execute("BEGIN")
        try:
            conn.execute(f"""
                INSERT INTO raw_prices
                    (date, code, open, high, low, close, volume, turnover, adj_factor, fetched_at)
                SELECT date, code, open, high, low, close, volume, turnover, adj_factor,
                       current_timestamp
                FROM {_TMP}
                {conflict_raw}
            """)
            conn.execute(f"""
                INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover)
                SELECT date, code, open, high, low, close, volume, turnover
                FROM {_TMP}
                WHERE open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL
                  AND close IS NOT NULL AND volume IS NOT NULL AND low <= high
                {conflict_proc}
            """)
            # TEMP TABLE への COUNT は prices_daily の全表走査より大幅に安価
            loaded = conn.execute(f"""
                SELECT COUNT(*) FROM {_TMP}
                WHERE open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL
                  AND close IS NOT NULL AND volume IS NOT NULL AND low <= high
            """).fetchone()[0]
            if not outer_tx:
                conn.execute("COMMIT")
        except Exception:
            if not outer_tx:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {_TMP}")

    logger.info("load_prices: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_master(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    bulk: bool = False,
    outer_tx: bool = False,
) -> int:
    """equities/master CSV → stocks

    bulk 引数は互換性のために受け付けるが無視する（master は常に upsert）。
    outer_tx  : True のとき BEGIN/COMMIT/ROLLBACK を行わない。
    """
    path = _sql_path(csv_path)

    conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE {_TMP} AS
        SELECT TRIM("Code") AS code, "CoName" AS name, "MktNm" AS market, "S33Nm" AS sector
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE TRIM("Code") != ''
    """)
    try:
        if not outer_tx:
            conn.execute("BEGIN")
        try:
            conn.execute(f"""
                INSERT INTO stocks (code, name, market, sector, updated_at)
                SELECT code, name, market, sector, current_timestamp
                FROM {_TMP}
                ON CONFLICT (code) DO UPDATE SET
                    name=EXCLUDED.name, market=EXCLUDED.market, sector=EXCLUDED.sector,
                    updated_at=EXCLUDED.updated_at
            """)
            loaded = conn.execute(f"SELECT COUNT(*) FROM {_TMP}").fetchone()[0]
            if not outer_tx:
                conn.execute("COMMIT")
        except Exception:
            if not outer_tx:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {_TMP}")

    logger.info("load_master: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_financials(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    bulk: bool = False,
    outer_tx: bool = False,
) -> int:
    """fins/summary CSV → raw_financials & fundamentals

    bulk=True : 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
    outer_tx  : True のとき BEGIN/COMMIT/ROLLBACK を行わない。
    """
    path = _sql_path(csv_path)

    conflict_raw = (
        "ON CONFLICT (code, report_date, period_type) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (code, report_date, period_type) DO UPDATE SET "
            "revenue=EXCLUDED.revenue, operating_profit=EXCLUDED.operating_profit, "
            "net_income=EXCLUDED.net_income, eps=EXCLUDED.eps, roe=EXCLUDED.roe, "
            "fetched_at=EXCLUDED.fetched_at"
        )
    )
    conflict_proc = (
        "ON CONFLICT (code, report_date, period_type) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (code, report_date, period_type) DO UPDATE SET "
            "revenue=EXCLUDED.revenue, operating_profit=EXCLUDED.operating_profit, "
            "net_income=EXCLUDED.net_income, eps=EXCLUDED.eps, roe=EXCLUDED.roe"
        )
    )

    conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE {_TMP} AS
        SELECT
            TRIM("Code")                      AS code,
            TRY_CAST("DiscDate" AS DATE)      AS report_date,
            TRIM("CurPerType")                AS period_type,
            TRY_CAST("Sales" AS DOUBLE)       AS revenue,
            TRY_CAST("OP" AS DOUBLE)          AS operating_profit,
            TRY_CAST("NP" AS DOUBLE)          AS net_income,
            TRY_CAST("EPS" AS DOUBLE)         AS eps,
            TRY_CAST("ROE" AS DOUBLE)         AS roe
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE TRIM("Code") != ''
          AND TRY_CAST("DiscDate" AS DATE) IS NOT NULL
          AND TRIM("CurPerType") != ''
    """)
    try:
        if not outer_tx:
            conn.execute("BEGIN")
        try:
            conn.execute(f"""
                INSERT INTO raw_financials
                    (code, report_date, period_type, revenue, operating_profit, net_income,
                     eps, roe, fetched_at)
                SELECT code, report_date, period_type, revenue, operating_profit, net_income,
                       eps, roe, current_timestamp
                FROM {_TMP}
                {conflict_raw}
            """)
            conn.execute(f"""
                INSERT INTO fundamentals
                    (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe)
                SELECT code, report_date, period_type, revenue, operating_profit, net_income, eps, roe
                FROM {_TMP}
                {conflict_proc}
            """)
            loaded = conn.execute(f"SELECT COUNT(*) FROM {_TMP}").fetchone()[0]
            if not outer_tx:
                conn.execute("COMMIT")
        except Exception:
            if not outer_tx:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {_TMP}")

    logger.info("load_financials: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_calendar(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    bulk: bool = False,
    outer_tx: bool = False,
) -> int:
    """markets/calendar CSV → market_calendar

    HolDiv="1" → is_trading_day=False（休日）

    bulk=True : 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
    outer_tx  : True のとき BEGIN/COMMIT/ROLLBACK を行わない。
    """
    path = _sql_path(csv_path)

    conflict = (
        "ON CONFLICT (date) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (date) DO UPDATE SET "
            "is_trading_day=EXCLUDED.is_trading_day, is_half_day=EXCLUDED.is_half_day, "
            "is_sq_day=EXCLUDED.is_sq_day, holiday_name=EXCLUDED.holiday_name"
        )
    )

    conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE {_TMP} AS
        SELECT
            TRY_CAST("Date" AS DATE) AS date,
            coalesce("HolDiv", '0') != '1'  AS is_trading_day,
            coalesce("HalfDiv", '0') = '1'  AS is_half_day,
            coalesce("SQDiv", '0') = '1'    AS is_sq_day,
            CASE WHEN "HolName" IS NULL OR trim("HolName") = '' THEN NULL ELSE "HolName" END
                AS holiday_name
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
    """)
    try:
        if not outer_tx:
            conn.execute("BEGIN")
        try:
            conn.execute(f"""
                INSERT INTO market_calendar
                    (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
                SELECT date, is_trading_day, is_half_day, is_sq_day, holiday_name
                FROM {_TMP}
                {conflict}
            """)
            loaded = conn.execute(f"SELECT COUNT(*) FROM {_TMP}").fetchone()[0]
            if not outer_tx:
                conn.execute("COMMIT")
        except Exception:
            if not outer_tx:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {_TMP}")

    logger.info("load_calendar: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_topix(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    bulk: bool = False,
    outer_tx: bool = False,
) -> int:
    """indices/bars/daily/topix CSV → topix_daily

    bulk=True : 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
    outer_tx  : True のとき BEGIN/COMMIT/ROLLBACK を行わない。
    """
    path = _sql_path(csv_path)

    conflict = (
        "ON CONFLICT (date) DO NOTHING"
        if bulk
        else (
            "ON CONFLICT (date) DO UPDATE SET "
            "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close"
        )
    )

    conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE {_TMP} AS
        SELECT
            TRY_CAST("Date" AS DATE) AS date,
            TRY_CAST("O" AS DOUBLE)  AS open,
            TRY_CAST("H" AS DOUBLE)  AS high,
            TRY_CAST("L" AS DOUBLE)  AS low,
            TRY_CAST("C" AS DOUBLE)  AS close
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
          AND TRY_CAST("O" AS DOUBLE) IS NOT NULL
          AND TRY_CAST("H" AS DOUBLE) IS NOT NULL
          AND TRY_CAST("L" AS DOUBLE) IS NOT NULL
          AND TRY_CAST("C" AS DOUBLE) IS NOT NULL
          AND TRY_CAST("L" AS DOUBLE) <= TRY_CAST("H" AS DOUBLE)
    """)
    try:
        if not outer_tx:
            conn.execute("BEGIN")
        try:
            conn.execute(f"""
                INSERT INTO topix_daily (date, open, high, low, close)
                SELECT date, open, high, low, close
                FROM {_TMP}
                {conflict}
            """)
            loaded = conn.execute(f"SELECT COUNT(*) FROM {_TMP}").fetchone()[0]
            if not outer_tx:
                conn.execute("COMMIT")
        except Exception:
            if not outer_tx:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {_TMP}")

    logger.info("load_topix: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded
