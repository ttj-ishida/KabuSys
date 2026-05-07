"""
build_features 統合テスト — TOPIX 相対強度・品質スコア (Issue #257)
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.feature_engineering import build_features


TARGET = date(2024, 3, 1)
START = date(2023, 1, 1)


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_prices(
    conn, code: str, start: date, days: int, base: float = 1000.0
) -> None:
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        c = base * (1 + 0.01 * i)
        rows.append((d, code, c, c, c, c, 100_000, c * 600_000))  # turnover > 5億
    conn.executemany(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
        rows,
    )


def _insert_topix(conn, start: date, days: int, base: float = 2000.0) -> None:
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        c = base * (1 + 0.005 * i)
        rows.append((d, c, c, c, c))
    conn.executemany(
        "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT DO NOTHING",
        rows,
    )


def _insert_financials(conn, code: str) -> None:
    conn.executemany(
        "INSERT INTO raw_financials "
        "(code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, bps, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp) ON CONFLICT DO NOTHING",
        [
            (
                code,
                date(2023, 1, 1),
                "FYResultNotification",
                1_000_000,
                200_000,
                150_000,
                100,
                0.10,
                1000,
            ),
            (
                code,
                date(2024, 1, 1),
                "FYResultNotification",
                1_200_000,
                250_000,
                180_000,
                120,
                0.12,
                1100,
            ),
        ],
    )


class TestBuildFeaturesWithNewColumns:
    def test_topix_rel_columns_populated_when_topix_data_exists(self, conn):
        _insert_prices(conn, "1001", START, 430)
        _insert_topix(conn, START, 430)
        _insert_financials(conn, "1001")
        count = build_features(conn, TARGET)
        assert count == 1
        row = conn.execute(
            "SELECT topix_rel_20, topix_rel_60 FROM features WHERE date=? AND code=?",
            [TARGET, "1001"],
        ).fetchone()
        assert row is not None
        assert row[0] is not None and math.isfinite(row[0])
        assert row[1] is not None and math.isfinite(row[1])

    def test_topix_rel_columns_null_when_no_topix_data(self, conn):
        _insert_prices(conn, "1001", START, 430)
        # topix_daily にデータなし
        _insert_financials(conn, "1001")
        count = build_features(conn, TARGET)
        assert count == 1
        row = conn.execute(
            "SELECT topix_rel_20, topix_rel_60 FROM features WHERE date=? AND code=?",
            [TARGET, "1001"],
        ).fetchone()
        assert row[0] is None
        assert row[1] is None

    def test_quality_score_populated_when_fy_data_exists(self, conn):
        _insert_prices(conn, "1001", START, 430)
        _insert_topix(conn, START, 430)
        _insert_financials(conn, "1001")
        build_features(conn, TARGET)
        row = conn.execute(
            "SELECT quality_score FROM features WHERE date=? AND code=?",
            [TARGET, "1001"],
        ).fetchone()
        assert row is not None
        assert row[0] is not None and math.isfinite(row[0])

    def test_quality_score_null_when_no_financials(self, conn):
        _insert_prices(conn, "1001", START, 430)
        _insert_topix(conn, START, 430)
        # raw_financials にデータなし
        build_features(conn, TARGET)
        row = conn.execute(
            "SELECT quality_score FROM features WHERE date=? AND code=?",
            [TARGET, "1001"],
        ).fetchone()
        assert row is not None
        assert row[0] is None

    def test_idempotent(self, conn):
        _insert_prices(conn, "1001", START, 430)
        _insert_topix(conn, START, 430)
        _insert_financials(conn, "1001")
        build_features(conn, TARGET)
        build_features(conn, TARGET)
        count = conn.execute(
            "SELECT COUNT(*) FROM features WHERE date=?", [TARGET]
        ).fetchone()[0]
        assert count == 1  # 日付単位で置換されるため重複なし
