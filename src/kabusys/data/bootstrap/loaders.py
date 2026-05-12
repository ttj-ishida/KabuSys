from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def _sql_path(csv_path: Path) -> str:
    """Path を SQL 文字列リテラルとして安全に埋め込む（シングルクォートをエスケープ）。"""
    return str(csv_path).replace("\\", "/").replace("'", "''")


def load_prices(conn: duckdb.DuckDBPyConnection, csv_path: Path, bulk: bool = False) -> int:
    """equities/bars/daily CSV → raw_prices & prices_daily

    DuckDB の read_csv() でネイティブ読み込みする。Python 側の CSV 解析を排除し
    ベクトル化バッチ処理による高速化を実現する。

    bulk=True: 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
               ON CONFLICT DO NOTHING でバルク INSERT する。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
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

    if bulk:
        conn.execute("BEGIN")
    try:
        conn.execute(f"""
            INSERT INTO raw_prices
                (date, code, open, high, low, close, volume, turnover, adj_factor, fetched_at)
            SELECT
                TRY_CAST("Date" AS DATE),
                "Code",
                TRY_CAST("O" AS DOUBLE),
                TRY_CAST("H" AS DOUBLE),
                TRY_CAST("L" AS DOUBLE),
                TRY_CAST("C" AS DOUBLE),
                TRY_CAST("Vo" AS BIGINT),
                TRY_CAST("Va" AS DOUBLE),
                TRY_CAST("AdjFactor" AS DOUBLE),
                current_timestamp
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
              AND "Code" IS NOT NULL AND trim("Code") != ''
            {conflict_raw}
        """)

        before = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchone()[0]
        conn.execute(f"""
            INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover)
            SELECT
                TRY_CAST("Date" AS DATE),
                "Code",
                TRY_CAST("O" AS DOUBLE),
                TRY_CAST("H" AS DOUBLE),
                TRY_CAST("L" AS DOUBLE),
                TRY_CAST("C" AS DOUBLE),
                TRY_CAST("Vo" AS BIGINT),
                TRY_CAST("Va" AS DOUBLE)
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
              AND "Code" IS NOT NULL AND trim("Code") != ''
              AND TRY_CAST("O" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("H" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("L" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("C" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("Vo" AS BIGINT) IS NOT NULL
              AND TRY_CAST("L" AS DOUBLE) <= TRY_CAST("H" AS DOUBLE)
            {conflict_proc}
        """)
        loaded = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchone()[0] - before

        if bulk:
            conn.execute("COMMIT")
    except Exception:
        if bulk:
            conn.execute("ROLLBACK")
        raise

    logger.info("load_prices: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_master(conn: duckdb.DuckDBPyConnection, csv_path: Path, bulk: bool = False) -> int:
    """equities/master CSV → stocks

    bulk 引数は互換性のために受け付けるが無視する（master は常に upsert）。
    """
    path = _sql_path(csv_path)

    before = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    conn.execute(f"""
        INSERT INTO stocks (code, name, market, sector, updated_at)
        SELECT
            "Code",
            "CoName",
            "MktNm",
            "S33Nm",
            current_timestamp
        FROM read_csv('{path}', nullstr='', all_varchar=true)
        WHERE "Code" IS NOT NULL AND trim("Code") != ''
        ON CONFLICT (code) DO UPDATE SET
            name=EXCLUDED.name, market=EXCLUDED.market, sector=EXCLUDED.sector,
            updated_at=EXCLUDED.updated_at
    """)
    loaded = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0] - before

    logger.info("load_master: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_financials(conn: duckdb.DuckDBPyConnection, csv_path: Path, bulk: bool = False) -> int:
    """fins/summary CSV → raw_financials & fundamentals

    bulk=True: 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
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

    if bulk:
        conn.execute("BEGIN")
    try:
        conn.execute(f"""
            INSERT INTO raw_financials
                (code, report_date, period_type, revenue, operating_profit, net_income,
                 eps, roe, fetched_at)
            SELECT
                "Code",
                TRY_CAST("DiscDate" AS DATE),
                "CurPerType",
                TRY_CAST("Sales" AS DOUBLE),
                TRY_CAST("OP" AS DOUBLE),
                TRY_CAST("NP" AS DOUBLE),
                TRY_CAST("EPS" AS DOUBLE),
                TRY_CAST("ROE" AS DOUBLE),
                current_timestamp
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE "Code" IS NOT NULL AND trim("Code") != ''
              AND TRY_CAST("DiscDate" AS DATE) IS NOT NULL
              AND "CurPerType" IS NOT NULL AND trim("CurPerType") != ''
            {conflict_raw}
        """)

        before = conn.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0]
        conn.execute(f"""
            INSERT INTO fundamentals
                (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe)
            SELECT
                "Code",
                TRY_CAST("DiscDate" AS DATE),
                "CurPerType",
                TRY_CAST("Sales" AS DOUBLE),
                TRY_CAST("OP" AS DOUBLE),
                TRY_CAST("NP" AS DOUBLE),
                TRY_CAST("EPS" AS DOUBLE),
                TRY_CAST("ROE" AS DOUBLE)
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE "Code" IS NOT NULL AND trim("Code") != ''
              AND TRY_CAST("DiscDate" AS DATE) IS NOT NULL
              AND "CurPerType" IS NOT NULL AND trim("CurPerType") != ''
            {conflict_proc}
        """)
        loaded = conn.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0] - before

        if bulk:
            conn.execute("COMMIT")
    except Exception:
        if bulk:
            conn.execute("ROLLBACK")
        raise

    logger.info("load_financials: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_calendar(conn: duckdb.DuckDBPyConnection, csv_path: Path, bulk: bool = False) -> int:
    """markets/calendar CSV → market_calendar

    HolDiv="1" → is_trading_day=False（休日）

    bulk=True: 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
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

    if bulk:
        conn.execute("BEGIN")
    try:
        before = conn.execute("SELECT COUNT(*) FROM market_calendar").fetchone()[0]
        conn.execute(f"""
            INSERT INTO market_calendar
                (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
            SELECT
                TRY_CAST("Date" AS DATE),
                coalesce("HolDiv", '0') != '1',
                coalesce("HalfDiv", '0') = '1',
                coalesce("SQDiv", '0') = '1',
                CASE WHEN "HolName" IS NULL OR trim("HolName") = '' THEN NULL ELSE "HolName" END
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
            {conflict}
        """)
        loaded = conn.execute("SELECT COUNT(*) FROM market_calendar").fetchone()[0] - before

        if bulk:
            conn.execute("COMMIT")
    except Exception:
        if bulk:
            conn.execute("ROLLBACK")
        raise

    logger.info("load_calendar: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_topix(conn: duckdb.DuckDBPyConnection, csv_path: Path, bulk: bool = False) -> int:
    """indices/bars/daily/topix CSV → topix_daily

    bulk=True: 月次ファイル用。呼び出し元が対象月を事前 DELETE 済みであること。
    bulk=False: 日次ファイル用。ON CONFLICT DO UPDATE で差分 upsert する。
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

    if bulk:
        conn.execute("BEGIN")
    try:
        before = conn.execute("SELECT COUNT(*) FROM topix_daily").fetchone()[0]
        conn.execute(f"""
            INSERT INTO topix_daily (date, open, high, low, close)
            SELECT
                TRY_CAST("Date" AS DATE),
                TRY_CAST("O" AS DOUBLE),
                TRY_CAST("H" AS DOUBLE),
                TRY_CAST("L" AS DOUBLE),
                TRY_CAST("C" AS DOUBLE)
            FROM read_csv('{path}', nullstr='', all_varchar=true)
            WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
              AND TRY_CAST("O" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("H" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("L" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("C" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("L" AS DOUBLE) <= TRY_CAST("H" AS DOUBLE)
            {conflict}
        """)
        loaded = conn.execute("SELECT COUNT(*) FROM topix_daily").fetchone()[0] - before

        if bulk:
            conn.execute("COMMIT")
    except Exception:
        if bulk:
            conn.execute("ROLLBACK")
        raise

    logger.info("load_topix: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded
