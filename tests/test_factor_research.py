"""
factor_research / feature_exploration モジュールのテスト

テスト方針:
  - インメモリ DuckDB を使用（外部 API・本番 DB へのアクセスなし）
  - 既知のデータを挿入して計算結果を検証する
  - Research 環境の分離（発注 API 未呼び出し）を保証する（Issue #11）
"""
from __future__ import annotations

import math
from datetime import date

import duckdb
import pytest

from kabusys.data.schema import init_schema
from kabusys.data.stats import zscore_normalize
from kabusys.research.factor_research import (
    calc_momentum,
    calc_volatility,
    calc_value,
)
from kabusys.research.feature_exploration import (
    calc_forward_returns,
    calc_ic,
    factor_summary,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """スキーマ初期化済みのインメモリ DuckDB 接続。"""
    conn = init_schema(":memory:")
    yield conn
    conn.close()


def _insert_prices(conn, rows: list[tuple]):
    """(date, code, open, high, low, close, volume, turnover) を prices_daily に挿入。"""
    conn.executemany(
        """
        INSERT INTO prices_daily
            (date, code, open, high, low, close, volume, turnover)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )


def _insert_financials(conn, rows: list[tuple]):
    """(code, report_date, period_type, revenue, operating_profit, net_income, eps, roe)
    を raw_financials に挿入。"""
    conn.executemany(
        """
        INSERT INTO raw_financials
            (code, report_date, period_type, revenue, operating_profit,
             net_income, eps, roe, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        ON CONFLICT DO NOTHING
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# calc_momentum
# ---------------------------------------------------------------------------

class TestCalcMomentum:
    def _make_price_series(self, conn, code: str, start_close: float, n_days: int, step: float = 1.0):
        """連続した日付の株価データを挿入するヘルパー。"""
        from datetime import timedelta
        base = date(2024, 1, 2)
        rows = []
        close = start_close
        for i in range(n_days):
            d = base + timedelta(days=i)
            rows.append((d, code, close, close + 10, close - 10, close, 1000, close * 1000))
            close += step
        _insert_prices(conn, rows)
        return base + timedelta(days=n_days - 1)

    def test_returns_list(self, db):
        target = self._make_price_series(db, "1001", 1000.0, 250)
        result = calc_momentum(db, target)
        assert isinstance(result, list)

    def test_columns_present(self, db):
        target = self._make_price_series(db, "1002", 1000.0, 250)
        result = calc_momentum(db, target)
        assert result, "データがない"
        row = result[0]
        assert "mom_1m" in row
        assert "mom_3m" in row
        assert "mom_6m" in row
        assert "ma200_dev" in row

    def test_positive_momentum(self, db):
        """価格が一定上昇している場合、モメンタムは正。"""
        target = self._make_price_series(db, "1003", 1000.0, 250, step=2.0)
        result = calc_momentum(db, target)
        row = next(r for r in result if r["code"] == "1003")
        assert row["mom_1m"] is not None and row["mom_1m"] > 0
        assert row["mom_3m"] is not None and row["mom_3m"] > 0

    def test_insufficient_data_returns_none(self, db):
        """データが少なすぎる場合、長期モメンタムは None。"""
        from datetime import timedelta
        # 30 日分しかないので mom_3m/mom_6m は None になる
        base = date(2024, 6, 1)
        rows = [(base + timedelta(days=i), "1004", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000)
                for i in range(30)]
        _insert_prices(db, rows)
        result = calc_momentum(db, base + timedelta(days=29))
        row = next((r for r in result if r["code"] == "1004"), None)
        assert row is not None
        assert row["mom_3m"] is None
        assert row["mom_6m"] is None

    def test_empty_table_returns_empty(self, db):
        result = calc_momentum(db, date(2024, 1, 5))
        assert result == []


# ---------------------------------------------------------------------------
# calc_volatility
# ---------------------------------------------------------------------------

class TestCalcVolatility:
    def test_atr_positive(self, db):
        from datetime import timedelta
        base = date(2024, 2, 1)
        rows = [
            (base + timedelta(days=i), "2001",
             1000.0, 1020.0, 980.0, 1000.0, 1000, 1000000.0)
            for i in range(30)
        ]
        _insert_prices(db, rows)
        result = calc_volatility(db, base + timedelta(days=29))
        row = next(r for r in result if r["code"] == "2001")
        assert row["atr_20"] is not None and row["atr_20"] > 0

    def test_volume_ratio_one_when_constant(self, db):
        """出来高が一定の場合 volume_ratio ≒ 1.0。"""
        from datetime import timedelta
        base = date(2024, 3, 1)
        rows = [
            (base + timedelta(days=i), "2002",
             1000.0, 1010.0, 990.0, 1000.0, 5000, 5000000.0)
            for i in range(25)
        ]
        _insert_prices(db, rows)
        result = calc_volatility(db, base + timedelta(days=24))
        row = next(r for r in result if r["code"] == "2002")
        assert row["volume_ratio"] is not None
        assert abs(row["volume_ratio"] - 1.0) < 0.01

    def test_columns_present(self, db):
        from datetime import timedelta
        base = date(2024, 4, 1)
        rows = [(base + timedelta(days=i), "2003", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)
                for i in range(25)]
        _insert_prices(db, rows)
        result = calc_volatility(db, base + timedelta(days=24))
        row = next(r for r in result if r["code"] == "2003")
        assert "atr_20" in row
        assert "atr_pct" in row
        assert "avg_turnover" in row
        assert "volume_ratio" in row


# ---------------------------------------------------------------------------
# calc_value
# ---------------------------------------------------------------------------

class TestCalcValue:
    def test_per_calculation(self, db):
        """PER = close / eps が正しく計算される。"""
        d = date(2024, 5, 1)
        _insert_prices(db, [(d, "3001", 2000.0, 2010.0, 1990.0, 2000.0, 1000, 2000000.0)])
        _insert_financials(db, [("3001", date(2024, 3, 31), "Q4", 1e9, 2e8, 1e8, 100.0, 0.10)])
        result = calc_value(db, d)
        row = next(r for r in result if r["code"] == "3001")
        assert row["per"] is not None
        assert abs(row["per"] - 20.0) < 0.01  # 2000 / 100 = 20

    def test_per_none_when_eps_zero(self, db):
        """EPS が 0 の場合 per は None。"""
        d = date(2024, 5, 2)
        _insert_prices(db, [(d, "3002", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        _insert_financials(db, [("3002", date(2024, 3, 31), "Q4", 5e8, 1e8, 5e7, 0.0, 0.05)])
        result = calc_value(db, d)
        row = next(r for r in result if r["code"] == "3002")
        assert row["per"] is None

    def test_roe_returned(self, db):
        d = date(2024, 5, 3)
        _insert_prices(db, [(d, "3003", 1500.0, 1510.0, 1490.0, 1500.0, 1000, 1500000.0)])
        _insert_financials(db, [("3003", date(2024, 3, 31), "Q4", 1e9, 3e8, 2e8, 200.0, 0.15)])
        result = calc_value(db, d)
        row = next(r for r in result if r["code"] == "3003")
        assert row["roe"] is not None
        assert abs(float(row["roe"]) - 0.15) < 0.001

    def test_no_financials_returns_none_per(self, db):
        """財務データがない場合 per は None。"""
        d = date(2024, 5, 4)
        _insert_prices(db, [(d, "3004", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        result = calc_value(db, d)
        row = next((r for r in result if r["code"] == "3004"), None)
        assert row is not None
        assert row["per"] is None


# ---------------------------------------------------------------------------
# zscore_normalize
# ---------------------------------------------------------------------------

class TestZscoreNormalize:
    def test_mean_near_zero(self):
        records = [
            {"code": "A", "factor": 10.0},
            {"code": "B", "factor": 20.0},
            {"code": "C", "factor": 30.0},
        ]
        result = zscore_normalize(records, ["factor"])
        values = [r["factor"] for r in result]
        assert abs(sum(values) / len(values)) < 1e-10

    def test_std_near_one(self):
        records = [{"code": str(i), "factor": float(i)} for i in range(10)]
        result = zscore_normalize(records, ["factor"])
        values = [r["factor"] for r in result]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        assert abs(std - 1.0) < 1e-10

    def test_none_preserved(self):
        records = [
            {"code": "A", "factor": 10.0},
            {"code": "B", "factor": None},
            {"code": "C", "factor": 30.0},
        ]
        result = zscore_normalize(records, ["factor"])
        assert result[1]["factor"] is None

    def test_original_not_mutated(self):
        records = [{"code": "A", "factor": 10.0}, {"code": "B", "factor": 20.0}]
        original_val = records[0]["factor"]
        zscore_normalize(records, ["factor"])
        assert records[0]["factor"] == original_val  # 元は変更されない

    def test_single_record_unchanged(self):
        records = [{"code": "A", "factor": 100.0}]
        result = zscore_normalize(records, ["factor"])
        assert result[0]["factor"] == 100.0

    def test_constant_values_unchanged(self):
        """全銘柄が同じ値の場合 std=0 → 変更なし。"""
        records = [{"code": str(i), "factor": 5.0} for i in range(5)]
        result = zscore_normalize(records, ["factor"])
        for r in result:
            assert r["factor"] == 5.0


# ---------------------------------------------------------------------------
# calc_forward_returns
# ---------------------------------------------------------------------------

class TestCalcForwardReturns:
    def test_default_horizons(self, db):
        from datetime import timedelta
        base = date(2024, 7, 1)
        rows = [(base + timedelta(days=i), "4001", 1000.0 + i * 10, 1010.0 + i * 10,
                 990.0 + i * 10, 1000.0 + i * 10, 1000, 1000000.0)
                for i in range(30)]
        _insert_prices(db, rows)
        result = calc_forward_returns(db, base)
        row = next(r for r in result if r["code"] == "4001")
        assert "fwd_1d" in row
        assert "fwd_5d" in row
        assert "fwd_21d" in row

    def test_fwd_1d_value(self, db):
        """翌日リターン = (close_t+1 - close_t) / close_t。"""
        from datetime import timedelta
        base = date(2024, 8, 1)
        _insert_prices(db, [
            (base, "4002", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0),
            (base + timedelta(days=1), "4002", 1100.0, 1110.0, 1090.0, 1100.0, 1000, 1100000.0),
        ])
        result = calc_forward_returns(db, base, horizons=[1])
        row = next(r for r in result if r["code"] == "4002")
        assert row["fwd_1d"] is not None
        assert abs(row["fwd_1d"] - 0.1) < 0.001  # (1100 - 1000) / 1000 = 0.1

    def test_none_when_no_future_data(self, db):
        """将来データが存在しない場合 fwd_Xd は None。"""
        d = date(2024, 9, 30)
        _insert_prices(db, [(d, "4003", 1000.0, 1010.0, 990.0, 1000.0, 1000, 1000000.0)])
        result = calc_forward_returns(db, d, horizons=[1])
        row = next(r for r in result if r["code"] == "4003")
        assert row["fwd_1d"] is None


# ---------------------------------------------------------------------------
# calc_ic
# ---------------------------------------------------------------------------

class TestCalcIC:
    def test_perfect_positive_correlation(self):
        """ファクターと将来リターンが完全一致 → IC ≒ 1。"""
        codes = [str(i) for i in range(10)]
        factor = [{"code": c, "factor": float(i)} for i, c in enumerate(codes)]
        fwd = [{"code": c, "fwd_1d": float(i)} for i, c in enumerate(codes)]
        ic = calc_ic(factor, fwd, "factor", "fwd_1d")
        assert ic is not None and abs(ic - 1.0) < 0.01

    def test_perfect_negative_correlation(self):
        codes = [str(i) for i in range(10)]
        factor = [{"code": c, "factor": float(i)} for i, c in enumerate(codes)]
        fwd = [{"code": c, "fwd_1d": float(9 - i)} for i, c in enumerate(codes)]
        ic = calc_ic(factor, fwd, "factor", "fwd_1d")
        assert ic is not None and abs(ic - (-1.0)) < 0.01

    def test_none_excluded(self):
        """None 値は除外して計算される。"""
        factor = [
            {"code": "A", "factor": 1.0},
            {"code": "B", "factor": None},
            {"code": "C", "factor": 3.0},
            {"code": "D", "factor": 4.0},
        ]
        fwd = [
            {"code": "A", "fwd_1d": 1.0},
            {"code": "B", "fwd_1d": 2.0},
            {"code": "C", "fwd_1d": 3.0},
            {"code": "D", "fwd_1d": 4.0},
        ]
        ic = calc_ic(factor, fwd, "factor", "fwd_1d")
        assert ic is not None

    def test_insufficient_data_returns_none(self):
        factor = [{"code": "A", "factor": 1.0}, {"code": "B", "factor": 2.0}]
        fwd = [{"code": "A", "fwd_1d": 1.0}, {"code": "B", "fwd_1d": 2.0}]
        assert calc_ic(factor, fwd, "factor", "fwd_1d") is None


# ---------------------------------------------------------------------------
# factor_summary
# ---------------------------------------------------------------------------

class TestFactorSummary:
    def test_basic_stats(self):
        records = [{"code": str(i), "factor": float(i + 1)} for i in range(5)]
        summary = factor_summary(records, ["factor"])
        s = summary["factor"]
        assert s["count"] == 5
        assert abs(s["mean"] - 3.0) < 1e-10
        assert s["min"] == 1.0
        assert s["max"] == 5.0

    def test_empty_column_returns_none_stats(self):
        records = [{"code": "A", "factor": None}]
        summary = factor_summary(records, ["factor"])
        s = summary["factor"]
        assert s["count"] == 0
        assert s["mean"] is None

    def test_median_odd(self):
        records = [{"code": str(i), "factor": float(i)} for i in [1, 3, 5, 7, 9]]
        summary = factor_summary(records, ["factor"])
        assert summary["factor"]["median"] == 5.0

    def test_median_even(self):
        records = [{"code": str(i), "factor": float(i)} for i in [1, 2, 3, 4]]
        summary = factor_summary(records, ["factor"])
        assert summary["factor"]["median"] == 2.5


# ---------------------------------------------------------------------------
# Issue #11: Research 環境分離の確認
# ---------------------------------------------------------------------------

class TestResearchIsolation:
    def test_no_kabu_api_import(self):
        """factor_research は kabuステーション API モジュールをインポートしない。"""
        import kabusys.research.factor_research as fr
        module_dict = vars(fr)
        assert "kabusys.execution" not in str(module_dict)

    def test_no_execution_import(self):
        """feature_exploration は execution モジュールをインポートしない。"""
        import kabusys.research.feature_exploration as fe
        module_dict = vars(fe)
        assert "kabusys.execution" not in str(module_dict)

    def test_uses_only_read_tables(self, db):
        """calc_momentum は prices_daily のみを参照し発注テーブルに書き込まない。"""
        before = db.execute("SELECT COUNT(*) FROM signal_queue").fetchone()[0]
        calc_momentum(db, date(2024, 1, 5))
        after = db.execute("SELECT COUNT(*) FROM signal_queue").fetchone()[0]
        assert before == after  # signal_queue に変化なし
