"""
TOPIX MA (MA25/MA75/MA200) 事前計算・保存機能のテスト (Issue #349)
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pytest

from kabusys.data.schema import init_schema


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_topix(conn: duckdb.DuckDBPyConnection, start: date, count: int, base: float = 2000.0) -> None:
    """count 日分の TOPIX データを挿入（close は base + 日連番）"""
    rows = []
    for i in range(count):
        d = start + timedelta(days=i)
        close = base + i
        rows.append((d, close, close, close, close))
    conn.executemany(
        "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
        rows,
    )


# ---------------------------------------------------------------------------
# schema: topix_daily に MA 列が存在することを確認
# ---------------------------------------------------------------------------

class TestTopixDailySchema:
    def test_ma_columns_exist_in_new_db(self, conn):
        """新規 DB では topix_daily に ma25/ma75/ma200 列が存在する"""
        cols = {r[1] for r in conn.execute("PRAGMA table_info('topix_daily')").fetchall()}
        assert "ma25" in cols
        assert "ma75" in cols
        assert "ma200" in cols

    def test_ma_columns_are_nullable(self, conn):
        """MA 列は NULL 許容（データ不足時は NULL のまま）"""
        d = date(2024, 1, 1)
        conn.execute(
            "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
            [d, 2000, 2000, 2000, 2000],
        )
        row = conn.execute("SELECT ma25, ma75, ma200 FROM topix_daily WHERE date = ?", [d]).fetchone()
        assert row is not None
        assert row[0] is None
        assert row[1] is None
        assert row[2] is None


# ---------------------------------------------------------------------------
# ensure_topix_ma_columns: 既存 DB への移行（冪等性）
# ---------------------------------------------------------------------------

class TestEnsureTopixMaColumns:
    def test_ensure_is_idempotent(self, conn):
        """2 回呼んでもエラーにならない"""
        from kabusys.strategy.feature_engineering import ensure_topix_ma_columns

        ensure_topix_ma_columns(conn)
        ensure_topix_ma_columns(conn)  # 2 回目もエラーなし

        cols = {r[1] for r in conn.execute("PRAGMA table_info('topix_daily')").fetchall()}
        assert "ma25" in cols
        assert "ma75" in cols
        assert "ma200" in cols

    def test_ensure_on_db_without_columns(self):
        """ma 列のない既存 DB に列を追加できる"""
        from kabusys.strategy.feature_engineering import ensure_topix_ma_columns

        c = duckdb.connect(":memory:")
        c.execute("""
            CREATE TABLE topix_daily (
                date  DATE PRIMARY KEY,
                open  DOUBLE NOT NULL,
                high  DOUBLE NOT NULL,
                low   DOUBLE NOT NULL,
                close DOUBLE NOT NULL
            )
        """)
        # MA 列なし状態で ensure を呼ぶ
        ensure_topix_ma_columns(c)

        cols = {r[1] for r in c.execute("PRAGMA table_info('topix_daily')").fetchall()}
        assert "ma25" in cols
        assert "ma75" in cols
        assert "ma200" in cols
        c.close()


# ---------------------------------------------------------------------------
# update_topix_ma: MA を計算して topix_daily に保存
# ---------------------------------------------------------------------------

class TestUpdateTopixMa:
    def test_returns_false_when_no_data(self, conn):
        """対象日付のデータがない場合 False を返す"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        result = update_topix_ma(conn, date(2024, 1, 1))
        assert result is False

    def test_returns_true_when_data_exists(self, conn):
        """対象日付のデータがある場合 True を返す"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2024, 1, 1), 1)
        result = update_topix_ma(conn, date(2024, 1, 1))
        assert result is True

    def test_ma_is_null_when_insufficient_data(self, conn):
        """データ不足（25 日未満）のとき MA は NULL"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2024, 1, 1), 10)  # 10 日分のみ
        update_topix_ma(conn, date(2024, 1, 10))
        row = conn.execute(
            "SELECT ma25, ma75, ma200 FROM topix_daily WHERE date = ?", [date(2024, 1, 10)]
        ).fetchone()
        assert row[0] is None  # ma25: 25 日未満
        assert row[1] is None  # ma75: 75 日未満
        assert row[2] is None  # ma200: 200 日未満

    def test_ma25_computed_when_25_days_available(self, conn):
        """25 日分のデータがあれば ma25 が計算される"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2024, 1, 1), 25, base=2000.0)
        update_topix_ma(conn, date(2024, 1, 25))
        row = conn.execute(
            "SELECT ma25, ma75, ma200 FROM topix_daily WHERE date = ?", [date(2024, 1, 25)]
        ).fetchone()
        # 2000, 2001, ..., 2024 の平均 = 2012.0
        assert row[0] is not None
        assert abs(row[0] - 2012.0) < 0.01
        assert row[1] is None   # ma75: まだ不足
        assert row[2] is None   # ma200: まだ不足

    def test_ma75_computed_when_75_days_available(self, conn):
        """75 日分のデータがあれば ma75 も計算される"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2024, 1, 1), 75, base=2000.0)
        update_topix_ma(conn, date(2024, 3, 15))
        row = conn.execute(
            "SELECT ma25, ma75, ma200 FROM topix_daily WHERE date = ?", [date(2024, 3, 15)]
        ).fetchone()
        assert row[0] is not None  # ma25 あり
        assert row[1] is not None  # ma75 あり
        assert row[2] is None      # ma200: まだ不足

    def test_all_ma_computed_when_200_days_available(self, conn):
        """200 日分のデータがあれば ma25/ma75/ma200 すべて計算される"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2023, 1, 1), 200, base=2000.0)
        target = date(2023, 1, 1) + timedelta(days=199)
        update_topix_ma(conn, target)
        row = conn.execute(
            "SELECT ma25, ma75, ma200 FROM topix_daily WHERE date = ?", [target]
        ).fetchone()
        assert row[0] is not None  # ma25
        assert row[1] is not None  # ma75
        assert row[2] is not None  # ma200

    def test_update_is_idempotent(self, conn):
        """同じ日付を 2 回更新してもエラーにならず同じ値を返す"""
        from kabusys.strategy.feature_engineering import update_topix_ma

        _insert_topix(conn, date(2024, 1, 1), 25, base=2000.0)
        update_topix_ma(conn, date(2024, 1, 25))
        update_topix_ma(conn, date(2024, 1, 25))  # 2 回目
        row = conn.execute(
            "SELECT ma25 FROM topix_daily WHERE date = ?", [date(2024, 1, 25)]
        ).fetchone()
        assert row[0] is not None
