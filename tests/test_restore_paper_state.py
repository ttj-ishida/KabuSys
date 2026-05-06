# tests/test_restore_paper_state.py
"""_restore_paper_state のユニットテスト。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kabusys.run_execution import _restore_paper_state


def _make_db(tmp_path: Path) -> Path:
    """テスト用 paper_trading.db を作成し、パスを返す。"""
    db_path = tmp_path / "paper_trading.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE orders (
            side TEXT, code TEXT, filled_qty INTEGER, avg_fill_price REAL
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestRestorePaperStateNoDb:
    def test_returns_initial_cash_when_no_db(self, tmp_path):
        path = tmp_path / "nonexistent.db"
        cash, positions = _restore_paper_state(path, 10_000_000.0)
        assert cash == 10_000_000.0
        assert positions == []


class TestRestorePaperStateEmpty:
    def test_returns_initial_cash_with_no_orders(self, tmp_path):
        db_path = _make_db(tmp_path)
        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0
        assert positions == []


class TestRestorePaperStateBuyOnly:
    def test_single_buy_reduces_cash(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            ("buy", "1234", 100, 1500.0),
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0 - 100 * 1500.0
        assert len(positions) == 1
        assert positions[0].code == "1234"
        assert positions[0].qty == 100
        assert positions[0].avg_price == 1500.0

    def test_multiple_buys_same_code_aggregated(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("buy", "1234", 100, 1000.0),
                ("buy", "1234", 200, 2000.0),
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        expected_cash = 10_000_000.0 - 100 * 1000.0 - 200 * 2000.0
        assert cash == expected_cash
        assert len(positions) == 1
        assert positions[0].qty == 300
        # avg_price = total_cost / total_qty = (100*1000 + 200*2000) / 300
        expected_avg = (100 * 1000.0 + 200 * 2000.0) / 300
        assert abs(positions[0].avg_price - expected_avg) < 0.01


class TestRestorePaperStateSell:
    def test_sell_removes_position_and_increases_cash(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("buy", "1234", 100, 1000.0),
                ("sell", "1234", 100, 1200.0),
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        expected_cash = 10_000_000.0 - 100 * 1000.0 + 100 * 1200.0
        assert cash == expected_cash
        assert positions == []  # net_qty = 0, position は残らない

    def test_partial_sell_leaves_remaining_position(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("buy", "1234", 200, 1000.0),
                ("sell", "1234", 100, 1200.0),
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert len(positions) == 1
        assert positions[0].qty == 100

    def test_multiple_codes(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("buy", "1234", 100, 1000.0),
                ("buy", "5678", 50, 2000.0),
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        codes = {p.code for p in positions}
        assert codes == {"1234", "5678"}
        assert len(positions) == 2


class TestRestorePaperStateNullPrice:
    def test_null_avg_fill_price_is_excluded(self, tmp_path):
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        # avg_fill_price=NULL（未約定）は集計から除外される
        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            ("buy", "1234", 100, None),
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0
        assert positions == []


class TestRestorePaperStateBrokenDb:
    def test_missing_table_returns_initial(self, tmp_path):
        db_path = tmp_path / "broken.db"
        # orders テーブルなしの空 DB
        sqlite3.connect(str(db_path)).close()
        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0
        assert positions == []


class TestRestorePaperStateSideNormalization:
    def test_unknown_side_is_skipped(self, tmp_path):
        """未知の side 値（"BUY" ではなく大文字など以外）は除外される。"""
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            ("unknown_side", "1234", 100, 1000.0),
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0  # 未知 side は現金に影響しない
        assert positions == []

    def test_uppercase_buy_is_treated_as_buy(self, tmp_path):
        """大文字 "BUY" も lower() 正規化で buy として扱う。"""
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            ("BUY", "1234", 100, 1000.0),
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert cash == 10_000_000.0 - 100 * 1000.0
        assert len(positions) == 1
        assert positions[0].code == "1234"

    def test_uppercase_sell_is_treated_as_sell(self, tmp_path):
        """大文字 "SELL" も lower() 正規化で sell として扱う。"""
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("BUY", "1234", 100, 1000.0),
                ("SELL", "1234", 100, 1200.0),
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        expected_cash = 10_000_000.0 - 100 * 1000.0 + 100 * 1200.0
        assert cash == expected_cash
        assert positions == []  # 全量売却後はポジション 0


class TestRestorePaperStateShortPosition:
    def test_net_qty_negative_position_is_skipped(self, tmp_path):
        """sell > buy でネット数量が負（ショート）になる場合はポジション生成しない。"""
        db_path = _make_db(tmp_path)
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            [
                ("buy", "1234", 100, 1000.0),
                ("sell", "1234", 200, 1200.0),  # 売り超過
            ],
        )
        conn.commit()
        conn.close()

        cash, positions = _restore_paper_state(db_path, 10_000_000.0)
        assert positions == []  # ショートポジションは生成しない
