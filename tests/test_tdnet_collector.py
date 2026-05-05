"""TDnet 開示収集モジュールのユニットテスト"""
from __future__ import annotations

import duckdb
import pytest


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

_DISCLOSURE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_disclosures (
        id              VARCHAR   NOT NULL PRIMARY KEY,
        disclosed_at    TIMESTAMP NOT NULL,
        code            VARCHAR,
        company_name    VARCHAR,
        title           VARCHAR,
        document_url    VARCHAR,
        document_type   VARCHAR,
        source          VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
        fetched_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS disclosure_events (
        id               VARCHAR   NOT NULL PRIMARY KEY,
        disclosed_at     TIMESTAMP NOT NULL,
        code             VARCHAR,
        event_type       VARCHAR   NOT NULL,
        event_score      DOUBLE    NOT NULL,
        buy_caution      BOOLEAN   NOT NULL DEFAULT false,
        hold_caution     BOOLEAN   NOT NULL DEFAULT false,
        review_required  BOOLEAN   NOT NULL DEFAULT false,
        title            VARCHAR,
        source           VARCHAR   NOT NULL CHECK (source IN ('tdnet', 'edinet')),
        classified_at    TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]


@pytest.fixture
def disc_db():
    conn = duckdb.connect(":memory:")
    for ddl in _DISCLOSURE_DDL:
        conn.execute(ddl)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Task 1: スキーマテスト
# ---------------------------------------------------------------------------


def test_raw_disclosures_table_exists(disc_db):
    """raw_disclosures テーブルが正しく作成されることを確認する。"""
    result = disc_db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'raw_disclosures' "
        "ORDER BY column_name"
    ).fetchall()
    columns = {row[0] for row in result}
    assert "id" in columns
    assert "disclosed_at" in columns
    assert "code" in columns
    assert "source" in columns
    assert "fetched_at" in columns


def test_disclosure_events_table_exists(disc_db):
    """disclosure_events テーブルが正しく作成されることを確認する。"""
    result = disc_db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'disclosure_events' "
        "ORDER BY column_name"
    ).fetchall()
    columns = {row[0] for row in result}
    assert "id" in columns
    assert "event_type" in columns
    assert "event_score" in columns
    assert "buy_caution" in columns
    assert "review_required" in columns
