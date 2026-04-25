from __future__ import annotations

import csv
import gzip
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

_CHUNK = 10_000


def _to_float(v: Any) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iter_gz(csv_path: Path):
    """gzip CSV を行ごとに dict で yield する。"""
    with gzip.open(csv_path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def load_prices(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """equities/bars/daily CSV → raw_prices & prices_daily

    Bulk CSV カラム: Date, Code, O, H, L, C, Vo, Va, AdjFactor
    （UL, LL, AdjO/H/L/C/Vo は保存しない）
    """
    loaded = 0
    buf_raw: list[tuple] = []
    buf_proc: list[tuple] = []
    fetched_at = _now()

    def _flush():
        nonlocal loaded
        if buf_raw:
            conn.executemany(
                "INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, adj_factor, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (date, code) DO UPDATE SET "
                "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, "
                "volume=EXCLUDED.volume, turnover=EXCLUDED.turnover, adj_factor=EXCLUDED.adj_factor, "
                "fetched_at=EXCLUDED.fetched_at",
                buf_raw,
            )
        if buf_proc:
            conn.executemany(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (date, code) DO UPDATE SET "
                "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, "
                "volume=EXCLUDED.volume, turnover=EXCLUDED.turnover",
                buf_proc,
            )
        loaded += len(buf_proc)
        buf_raw.clear()
        buf_proc.clear()

    for row in _iter_gz(csv_path):
        date = row.get("Date", "").strip()
        code = row.get("Code", "").strip()
        if not date or not code:
            logger.warning("load_prices: PK 欠損行をスキップ: %s", row)
            continue

        o = _to_float(row.get("O"))
        h = _to_float(row.get("H"))
        lo = _to_float(row.get("L"))
        c = _to_float(row.get("C"))
        vol = _to_int(row.get("Vo"))
        va = _to_float(row.get("Va"))
        adj = _to_float(row.get("AdjFactor"))

        buf_raw.append((date, code, o, h, lo, c, vol, va, adj, fetched_at))

        # prices_daily: NOT NULL OHLCV 必須 / low <= high
        if None in (o, h, lo, c, vol):
            continue
        if lo > h:  # type: ignore[operator]
            continue
        buf_proc.append((date, code, o, h, lo, c, vol, va))

        if len(buf_raw) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_prices: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_master(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """equities/master CSV → stocks

    Bulk CSV カラム: Code, CoName, MktNm, S33Nm
    """
    loaded = 0
    buf: list[tuple] = []

    def _flush():
        nonlocal loaded
        if buf:
            conn.executemany(
                "INSERT INTO stocks (code, name, market, sector, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (code) DO UPDATE SET "
                "name=EXCLUDED.name, market=EXCLUDED.market, sector=EXCLUDED.sector, "
                "updated_at=EXCLUDED.updated_at",
                buf,
            )
            loaded += len(buf)
            buf.clear()

    now = _now()
    for row in _iter_gz(csv_path):
        code = row.get("Code", "").strip()
        if not code:
            logger.warning("load_master: code 欠損行をスキップ: %s", row)
            continue
        buf.append((code, row.get("CoName"), row.get("MktNm"), row.get("S33Nm"), now))
        if len(buf) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_master: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_financials(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """fins/summary CSV → raw_financials & fundamentals

    Bulk CSV カラム: Code, DiscDate, CurPerType, Sales, OP, NP, EPS, ROE
    """
    loaded = 0
    buf_raw: list[tuple] = []
    buf_proc: list[tuple] = []
    fetched_at = _now()

    def _flush():
        nonlocal loaded
        if buf_raw:
            conn.executemany(
                "INSERT INTO raw_financials (code, report_date, period_type, revenue, "
                "operating_profit, net_income, eps, roe, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (code, report_date, period_type) DO UPDATE SET "
                "revenue=EXCLUDED.revenue, operating_profit=EXCLUDED.operating_profit, "
                "net_income=EXCLUDED.net_income, eps=EXCLUDED.eps, roe=EXCLUDED.roe, "
                "fetched_at=EXCLUDED.fetched_at",
                buf_raw,
            )
        if buf_proc:
            conn.executemany(
                "INSERT INTO fundamentals (code, report_date, period_type, revenue, "
                "operating_profit, net_income, eps, roe) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (code, report_date, period_type) DO UPDATE SET "
                "revenue=EXCLUDED.revenue, operating_profit=EXCLUDED.operating_profit, "
                "net_income=EXCLUDED.net_income, eps=EXCLUDED.eps, roe=EXCLUDED.roe",
                buf_proc,
            )
        loaded += len(buf_proc)
        buf_raw.clear()
        buf_proc.clear()

    for row in _iter_gz(csv_path):
        code = row.get("Code", "").strip()
        report_date = row.get("DiscDate", "").strip()
        period_type = row.get("CurPerType", "").strip()
        if not code or not report_date or not period_type:
            logger.warning("load_financials: PK 欠損行をスキップ: %s", row)
            continue

        revenue = _to_float(row.get("Sales"))
        op = _to_float(row.get("OP"))
        np_ = _to_float(row.get("NP"))
        eps = _to_float(row.get("EPS"))
        roe = _to_float(row.get("ROE"))

        buf_raw.append((code, report_date, period_type, revenue, op, np_, eps, roe, fetched_at))
        buf_proc.append((code, report_date, period_type, revenue, op, np_, eps, roe))

        if len(buf_raw) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_financials: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_calendar(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """markets/calendar CSV → market_calendar

    Bulk CSV カラム: Date, HolDiv, HalfDiv, SQDiv, HolName
    HolDiv="1" → is_trading_day=False（休日）
    """
    loaded = 0
    buf: list[tuple] = []

    def _flush():
        nonlocal loaded
        if buf:
            conn.executemany(
                "INSERT INTO market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (date) DO UPDATE SET "
                "is_trading_day=EXCLUDED.is_trading_day, is_half_day=EXCLUDED.is_half_day, "
                "is_sq_day=EXCLUDED.is_sq_day, holiday_name=EXCLUDED.holiday_name",
                buf,
            )
            loaded += len(buf)
            buf.clear()

    for row in _iter_gz(csv_path):
        date = row.get("Date", "").strip()
        if not date:
            logger.warning("load_calendar: date 欠損行をスキップ: %s", row)
            continue
        is_trading = row.get("HolDiv", "0").strip() != "1"
        is_half = row.get("HalfDiv", "0").strip() == "1"
        is_sq = row.get("SQDiv", "0").strip() == "1"
        holiday_name = row.get("HolName", "").strip() or None
        buf.append((date, is_trading, is_half, is_sq, holiday_name))
        if len(buf) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_calendar: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_dividend(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """fins/dividend CSV → dividends

    Bulk CSV カラム: Code, PubDate, RefNo, ExDate, RecDate, PayDate, DivRate
    """
    loaded = 0
    buf: list[tuple] = []
    fetched_at = _now()

    def _flush():
        nonlocal loaded
        if buf:
            conn.executemany(
                "INSERT INTO dividends (code, pub_date, ref_no, ex_date, record_date, pay_date, div_rate, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (code, pub_date, ref_no) DO UPDATE SET "
                "ex_date=EXCLUDED.ex_date, record_date=EXCLUDED.record_date, "
                "pay_date=EXCLUDED.pay_date, div_rate=EXCLUDED.div_rate, fetched_at=EXCLUDED.fetched_at",
                buf,
            )
            loaded += len(buf)
            buf.clear()

    for row in _iter_gz(csv_path):
        code = row.get("Code", "").strip()
        pub_date = row.get("PubDate", "").strip()
        ref_no = row.get("RefNo", "").strip()
        if not code or not pub_date or not ref_no:
            logger.warning("load_dividend: PK 欠損行をスキップ: %s", row)
            continue
        ex_date = row.get("ExDate", "").strip() or None
        rec_date = row.get("RecDate", "").strip() or None
        pay_date = row.get("PayDate", "").strip() or None
        div_rate = _to_float(row.get("DivRate"))
        buf.append((code, pub_date, ref_no, ex_date, rec_date, pay_date, div_rate, fetched_at))
        if len(buf) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_dividend: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded


def load_topix(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """indices/bars/daily/topix CSV → topix_daily

    Bulk CSV カラム: Date, O, H, L, C
    """
    loaded = 0
    buf: list[tuple] = []

    def _flush():
        nonlocal loaded
        if buf:
            conn.executemany(
                "INSERT INTO topix_daily (date, open, high, low, close) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (date) DO UPDATE SET "
                "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close",
                buf,
            )
            loaded += len(buf)
            buf.clear()

    for row in _iter_gz(csv_path):
        date = row.get("Date", "").strip()
        if not date:
            logger.warning("load_topix: date 欠損行をスキップ: %s", row)
            continue
        o = _to_float(row.get("O"))
        h = _to_float(row.get("H"))
        lo = _to_float(row.get("L"))
        c = _to_float(row.get("C"))
        if None in (o, h, lo, c):
            logger.warning("load_topix: OHLC 欠損行をスキップ: %s", row)
            continue
        buf.append((date, o, h, lo, c))
        if len(buf) >= _CHUNK:
            _flush()

    _flush()
    logger.info("load_topix: %d 件ロード (%s)", loaded, csv_path.name)
    return loaded
