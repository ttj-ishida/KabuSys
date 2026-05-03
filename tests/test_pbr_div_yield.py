# tests/test_pbr_div_yield.py
import tomllib
from pathlib import Path

import duckdb
import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# Task 1: スキーマ・設定ファイル
# ---------------------------------------------------------------------------


class TestSchema:
    def test_raw_financials_has_bps_column(self):
        """init_schema 後に raw_financials に bps カラムが存在すること。"""
        conn = init_schema(":memory:")
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'raw_financials'"
            ).fetchall()
        }
        assert "bps" in cols, f"bps カラムが存在しない。現在のカラム: {cols}"
        conn.close()

    def test_migration_adds_bps_to_existing_db(self, tmp_path):
        """bps カラムがない既存 DB に init_schema を実行すると bps が追加されること。"""
        db_path = tmp_path / "test.db"
        # bps なしで DB を作成
        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE raw_financials (
                code VARCHAR NOT NULL,
                report_date DATE NOT NULL,
                period_type VARCHAR NOT NULL,
                eps DECIMAL(18,4),
                roe DECIMAL(10,6),
                fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                PRIMARY KEY (code, report_date, period_type)
            )
            """
        )
        conn.close()
        # init_schema でマイグレーション実行
        conn2 = init_schema(db_path)
        cols = {
            row[0]
            for row in conn2.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'raw_financials'"
            ).fetchall()
        }
        assert "bps" in cols
        conn2.close()

    def test_strategy_toml_loads_and_has_required_keys(self):
        """config/strategy.toml が存在し、必要なキーを持つこと。"""
        toml_path = Path(__file__).resolve().parents[1] / "config" / "strategy.toml"
        assert toml_path.exists(), "config/strategy.toml が存在しない"
        with open(toml_path, "rb") as f:
            cfg = tomllib.load(f)
        w = cfg["value_score"]["weights"]
        n = cfg["value_score"]["normalization"]
        assert set(w.keys()) == {"per", "pbr", "div_yield"}
        assert abs(sum(w.values()) - 1.0) < 1e-9, "重みの合計が 1.0 でない"
        assert "per_mid" in n
        assert "pbr_mid" in n
        assert "div_yield_max" in n


# ---------------------------------------------------------------------------
# Task 2: BPS 抽出
# ---------------------------------------------------------------------------

from kabusys.data import jquants_client as jq


class TestBpsExtraction:
    def test_save_financial_statements_stores_bps(self):
        """save_financial_statements が BookValuePerShare を raw_financials.bps に保存すること。"""
        conn = init_schema(":memory:")
        records = [
            {
                "LocalCode": "72030",
                "DisclosedDate": "2024-03-31",
                "TypeOfDocument": "Q4",
                "NetSales": "1000000",
                "OperatingProfit": "200000",
                "Profit": "150000",
                "EarningsPerShare": "100.0",
                "ROE": "0.15",
                "BookValuePerShare": "1500.0",
            }
        ]
        saved = jq.save_financial_statements(conn, records)
        assert saved == 1
        row = conn.execute(
            "SELECT bps FROM raw_financials WHERE code = '72030'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 1500.0) < 0.01
        conn.close()

    def test_save_financial_statements_handles_missing_bps(self):
        """BookValuePerShare がない場合 bps は NULL になること。"""
        conn = init_schema(":memory:")
        records = [
            {
                "LocalCode": "72031",
                "DisclosedDate": "2024-03-31",
                "TypeOfDocument": "Q4",
                "EarningsPerShare": "50.0",
                "ROE": "0.10",
                # BookValuePerShare なし
            }
        ]
        jq.save_financial_statements(conn, records)
        row = conn.execute(
            "SELECT bps FROM raw_financials WHERE code = '72031'"
        ).fetchone()
        assert row is not None
        assert row[0] is None
        conn.close()


# ---------------------------------------------------------------------------
# Task 3: 配当 ETL
# ---------------------------------------------------------------------------

from unittest.mock import patch

from kabusys.data.pipeline import run_dividends_etl


def _insert_dividends(conn, rows: list[tuple]) -> None:
    """(code, pub_date, ref_no, ex_date, record_date, pay_date, div_rate) を dividends に挿入。"""
    conn.executemany(
        """
        INSERT INTO dividends
            (code, pub_date, ref_no, ex_date, record_date, pay_date, div_rate, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, current_timestamp)
        ON CONFLICT (code, pub_date, ref_no) DO UPDATE SET
            div_rate = excluded.div_rate, fetched_at = excluded.fetched_at
        """,
        rows,
    )


class TestDividendsEtl:
    def test_save_dividends_stores_records(self):
        """save_dividends が dividends テーブルに div_rate を保存すること。"""
        conn = init_schema(":memory:")
        records = [
            {
                "Code": "72030",
                "PubDate": "2024-01-15",
                "RefNo": "001",
                "ExDate": "2024-03-27",
                "RecDate": "2024-03-31",
                "PayDate": "2024-06-01",
                "DivRate": "50.0",
            }
        ]
        saved = jq.save_dividends(conn, records)
        assert saved == 1
        row = conn.execute(
            "SELECT div_rate FROM dividends WHERE code = '72030' AND ref_no = '001'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 50.0) < 0.01
        conn.close()

    def test_save_dividends_is_idempotent(self):
        """同じレコードを2回保存しても重複しないこと（upsert）。"""
        conn = init_schema(":memory:")
        record = {
            "Code": "72030",
            "PubDate": "2024-01-15",
            "RefNo": "001",
            "ExDate": "2024-03-27",
            "RecDate": "2024-03-31",
            "PayDate": "2024-06-01",
            "DivRate": "50.0",
        }
        jq.save_dividends(conn, [record])
        record["DivRate"] = "60.0"  # 値を更新
        jq.save_dividends(conn, [record])
        rows = conn.execute("SELECT div_rate FROM dividends WHERE code = '72030'").fetchall()
        assert len(rows) == 1
        assert abs(float(rows[0][0]) - 60.0) < 0.01  # 更新後の値
        conn.close()

    def test_run_dividends_etl_calls_fetch_and_save(self):
        """run_dividends_etl が fetch_dividends / save_dividends を呼び出すこと。"""
        from datetime import date
        conn = init_schema(":memory:")
        fake_records = [
            {
                "Code": "72030",
                "PubDate": "2024-01-15",
                "RefNo": "001",
                "ExDate": "2024-03-27",
                "RecDate": "2024-03-31",
                "PayDate": "2024-06-01",
                "DivRate": "50.0",
            }
        ]
        with patch(
            "kabusys.data.pipeline.jq.fetch_dividends", return_value=fake_records
        ) as mock_fetch:
            fetched, saved = run_dividends_etl(
                conn, target_date=date(2024, 4, 1), id_token="dummy"
            )
        mock_fetch.assert_called_once_with(
            id_token="dummy",
            date_from=date(2017, 1, 1),  # _MIN_DATA_DATE (empty DB, no prior dividends)
            date_to=date(2024, 4, 1),
        )
        assert fetched == 1
        assert saved == 1
        conn.close()
