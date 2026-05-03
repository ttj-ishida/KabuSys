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
