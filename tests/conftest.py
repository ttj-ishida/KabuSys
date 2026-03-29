"""テスト共通フィクスチャ・定数

DuckDB の FK CASCADE 制約が古いバージョン（1.x 以前）で使えないため、
init_schema() の代わりに最小 DDL でテーブルを作成する共通フィクスチャを提供する。
"""
from __future__ import annotations

import duckdb
import sqlite3
import pytest
from kabusys.execution.order_repository import init_orders_db
from kabusys.monitoring.monitoring_db import init_monitoring_db

# テスト対象テーブルのみ作成（FK CASCADE/SET NULL を持つテーブルは除外）
MINIMAL_DDL = [
    """CREATE TABLE IF NOT EXISTS raw_prices (
        date        DATE          NOT NULL,
        code        VARCHAR       NOT NULL,
        open        DECIMAL(18,4),
        high        DECIMAL(18,4),
        low         DECIMAL(18,4),
        close       DECIMAL(18,4),
        volume      BIGINT,
        turnover    DECIMAL(18,2),
        fetched_at  TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        PRIMARY KEY (date, code)
    )""",
    """CREATE TABLE IF NOT EXISTS raw_financials (
        code            VARCHAR       NOT NULL,
        report_date     DATE          NOT NULL,
        period_type     VARCHAR       NOT NULL,
        revenue         DECIMAL(20,4),
        operating_profit DECIMAL(20,4),
        net_income      DECIMAL(20,4),
        eps             DECIMAL(18,4),
        roe             DECIMAL(10,6),
        fetched_at      TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        PRIMARY KEY (code, report_date, period_type)
    )""",
    """CREATE TABLE IF NOT EXISTS market_calendar (
        date            DATE        NOT NULL PRIMARY KEY,
        is_trading_day  BOOLEAN     NOT NULL,
        is_half_day     BOOLEAN     NOT NULL DEFAULT false,
        is_sq_day       BOOLEAN     NOT NULL DEFAULT false,
        holiday_name    VARCHAR
    )""",
]


@pytest.fixture
def mem_db():
    """テスト用インメモリ DuckDB（最小スキーマ）を返すフィクスチャ。

    init_schema() の FK CASCADE 問題を回避し、テスト対象テーブルのみ作成する。
    """
    conn = duckdb.connect(":memory:")
    for ddl in MINIMAL_DDL:
        conn.execute(ddl)
    yield conn
    conn.close()


@pytest.fixture
def sqlite_conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score FLOAT, signal_rank INTEGER)
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (date DATE, code VARCHAR, target_size INTEGER, entry_price FLOAT)
    """)
    yield conn
    conn.close()


@pytest.fixture
def monitoring_conn():
    """テスト用インメモリ SQLite（監視ログ DB スキーマ）を返すフィクスチャ。"""
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    yield conn
    conn.close()
