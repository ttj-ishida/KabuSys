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


# ---------------------------------------------------------------------------
# Task 4: 特徴量計算
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from kabusys.research.factor_research import calc_value


def _insert_prices(conn, rows: list[tuple]) -> None:
    """(date, code, open, high, low, close, volume, turnover) を prices_daily に挿入。"""
    conn.executemany(
        """
        INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )


def _insert_financials_with_bps(conn, rows: list[tuple]) -> None:
    """(code, report_date, period_type, eps, roe, bps) を raw_financials に挿入。"""
    conn.executemany(
        """
        INSERT INTO raw_financials
            (code, report_date, period_type, eps, roe, bps, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )


class TestCalcValuePbr:
    def test_pbr_calculation(self):
        """PBR = close / bps が正しく計算されること。"""
        conn = init_schema(":memory:")
        d = date(2024, 5, 1)
        _insert_prices(conn, [(d, "8001", 1500.0, 1510.0, 1490.0, 1500.0, 1000, 1500000.0)])
        _insert_financials_with_bps(conn, [("8001", date(2024, 3, 31), "Q4", 100.0, 0.10, 1000.0)])
        result = calc_value(conn, d)
        row = next(r for r in result if r["code"] == "8001")
        assert row["pbr"] is not None
        assert abs(row["pbr"] - 1.5) < 0.01  # 1500 / 1000 = 1.5
        conn.close()

    def test_pbr_none_when_bps_zero(self):
        """BPS が 0 の場合 pbr は None。"""
        conn = init_schema(":memory:")
        d = date(2024, 5, 2)
        _insert_prices(conn, [(d, "8002", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        _insert_financials_with_bps(conn, [("8002", date(2024, 3, 31), "Q4", 50.0, 0.05, 0.0)])
        result = calc_value(conn, d)
        row = next(r for r in result if r["code"] == "8002")
        assert row["pbr"] is None
        conn.close()


class TestCalcValueDivYield:
    def test_div_yield_calculation(self):
        """直近12ヶ月の配当合計 / close × 100 が div_yield になること。"""
        conn = init_schema(":memory:")
        d = date(2024, 5, 1)
        _insert_prices(conn, [(d, "9001", 2000.0, 2010.0, 1990.0, 2000.0, 1000, 2000000.0)])
        # 直近12ヶ月に2回配当（合計60円）
        _insert_dividends(conn, [
            ("9001", "2023-09-01", "001", "2023-09-27", "2023-09-30", "2023-12-01", 30.0),
            ("9001", "2024-03-01", "002", "2024-03-27", "2024-03-31", "2024-06-01", 30.0),
        ])
        result = calc_value(conn, d)
        row = next(r for r in result if r["code"] == "9001")
        assert row["div_yield"] is not None
        assert abs(row["div_yield"] - 3.0) < 0.01  # (30+30) / 2000 * 100 = 3.0%
        conn.close()

    def test_div_yield_none_when_no_dividends(self):
        """配当レコードがない場合 div_yield は None。"""
        conn = init_schema(":memory:")
        d = date(2024, 5, 3)
        _insert_prices(conn, [(d, "9002", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        result = calc_value(conn, d)
        row = next((r for r in result if r["code"] == "9002"), None)
        assert row is not None
        assert row["div_yield"] is None
        conn.close()

    def test_div_yield_excludes_old_dividends(self):
        """13ヶ月前の配当は集計対象外になること。"""
        conn = init_schema(":memory:")
        d = date(2024, 5, 1)
        _insert_prices(conn, [(d, "9003", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        # 13ヶ月前の配当（対象外）と直近12ヶ月内（対象）
        _insert_dividends(conn, [
            ("9003", "2023-01-01", "001", "2023-03-27", "2023-03-31", "2023-06-01", 100.0),  # 対象外
            ("9003", "2024-03-01", "002", "2024-03-27", "2024-03-31", "2024-06-01", 20.0),   # 対象
        ])
        result = calc_value(conn, d)
        row = next(r for r in result if r["code"] == "9003")
        assert row["div_yield"] is not None
        assert abs(row["div_yield"] - 2.0) < 0.01  # 20 / 1000 * 100 = 2.0%（100円は除外）
        conn.close()


# ---------------------------------------------------------------------------
# Task 5: バリュースコア
# ---------------------------------------------------------------------------

from kabusys.strategy.signal_generator import _compute_value_score, _load_value_config


def _default_config() -> dict:
    """テスト用デフォルト設定を返す。"""
    return {
        "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
        "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
    }


class TestValueScoreAllThree:
    def test_all_three_indicators(self):
        """3指標すべて有効なとき加重平均が正しいこと。"""
        cfg = _default_config()
        feat = {"per": 20.0, "pbr": 1.5, "div_yield": 3.0}
        score = _compute_value_score(feat, cfg)
        # per=20 → 0.5, pbr=1.5 → 0.5, div_yield=3.0 → 1.0
        # 0.50*0.5 + 0.30*0.5 + 0.20*1.0 = 0.25 + 0.15 + 0.20 = 0.60
        assert score is not None
        assert abs(score - 0.60) < 1e-9

    def test_low_per_high_score(self):
        """PER が低いほどスコアが高いこと。"""
        cfg = _default_config()
        score_low = _compute_value_score({"per": 10.0}, cfg)
        score_high = _compute_value_score({"per": 40.0}, cfg)
        assert score_low is not None and score_high is not None
        assert score_low > score_high

    def test_low_pbr_high_score(self):
        """PBR が低いほどスコアが高いこと。"""
        cfg = _default_config()
        score_low = _compute_value_score({"pbr": 0.5}, cfg)
        score_high = _compute_value_score({"pbr": 3.0}, cfg)
        assert score_low is not None and score_high is not None
        assert score_low > score_high

    def test_high_div_yield_high_score(self):
        """配当利回りが高いほどスコアが高いこと（上限 1.0）。"""
        cfg = _default_config()
        score_low = _compute_value_score({"div_yield": 1.0}, cfg)
        score_high = _compute_value_score({"div_yield": 5.0}, cfg)
        assert score_low is not None and score_high is not None
        assert score_low < score_high
        # 上限チェック: div_yield >= div_yield_max で score=1.0
        score_cap = _compute_value_score({"div_yield": 10.0}, cfg)
        assert abs(score_cap - 1.0) < 1e-9


class TestValueScorePartial:
    def test_pbr_missing_uses_per_and_div_yield(self):
        """PBR 欠損のとき PER と配当利回りで重み正規化して計算すること。"""
        cfg = _default_config()
        feat = {"per": 20.0, "div_yield": 3.0}  # pbr なし
        score = _compute_value_score(feat, cfg)
        # per=20 → 0.5, div_yield=3.0 → 1.0
        # total_w = 0.50 + 0.20 = 0.70
        # (0.50*0.5 + 0.20*1.0) / 0.70 = 0.45 / 0.70 ≈ 0.6429
        assert score is not None
        assert abs(score - 0.45 / 0.70) < 1e-6

    def test_all_missing_returns_none(self):
        """3指標すべて欠損のとき None を返すこと。"""
        cfg = _default_config()
        assert _compute_value_score({}, cfg) is None
        assert _compute_value_score({"per": None, "pbr": None, "div_yield": None}, cfg) is None


class TestValueScoreConfigDriven:
    def test_changing_per_mid_changes_score(self):
        """per_mid を変更するとスコアが変わること。"""
        feat = {"per": 20.0}
        cfg_default = _default_config()
        cfg_strict = {
            "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
            "normalization": {"per_mid": 10.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
        }
        score_default = _compute_value_score(feat, cfg_default)
        score_strict = _compute_value_score(feat, cfg_strict)
        # per_mid=20 → score=0.5; per_mid=10 → 1/(1+20/10)=1/3≈0.333
        assert score_default is not None and score_strict is not None
        assert score_default > score_strict

    def test_load_value_config_returns_dict_with_required_keys(self):
        """_load_value_config が weights と normalization キーを持つ dict を返すこと。"""
        cfg = _load_value_config()
        assert "weights" in cfg
        assert "normalization" in cfg
        assert "per" in cfg["weights"]
        assert "per_mid" in cfg["normalization"]
