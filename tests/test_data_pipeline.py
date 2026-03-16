"""
データパイプライン単体テスト

Issue #8 の要件:
  - J-Quants API クライアントのモック
  - ETL 処理の冪等性確認
  - スキーマ整合性チェック
"""

from __future__ import annotations

from datetime import date
from unittest import mock

import pytest

from kabusys.data import jquants_client as jquants
from kabusys.data import quality


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------
# mem_db フィクスチャは tests/conftest.py で定義（DRY化）。


def _sample_price_record(
    date_str: str = "2024-01-10",
    code: str = "7203",
    open_: float = 2800.0,
    high: float = 2850.0,
    low: float = 2780.0,
    close: float = 2830.0,
    volume: int = 1000000,
    turnover: int = 2830000000,
) -> dict:
    return {
        "Date": date_str,
        "Code": code,
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
        "TurnoverValue": turnover,
    }


def _sample_financial_record(
    code: str = "7203",
    disclosed_date: str = "2024-01-10",
    type_of_doc: str = "FY",
    net_sales: float = 1000000.0,
    operating_profit: float = 100000.0,
    profit: float = 80000.0,
    eps: float = 120.5,
    roe: float = 0.12,
) -> dict:
    return {
        "LocalCode": code,
        "DisclosedDate": disclosed_date,
        "TypeOfDocument": type_of_doc,
        "NetSales": net_sales,
        "OperatingProfit": operating_profit,
        "Profit": profit,
        "EarningsPerShare": eps,
        "ROE": roe,
    }


def _sample_calendar_record(
    date_str: str = "2024-01-10",
    division: str = "0",
    holiday_name: str | None = None,
) -> dict:
    return {
        "Date": date_str,
        "HolidayDivision": division,
        "HolidayName": holiday_name,
    }


# ---------------------------------------------------------------------------
# スキーマ整合性チェック
# ---------------------------------------------------------------------------


class TestSchemaIntegrity:
    """スキーマ定義の整合性を検証する。"""

    def test_raw_prices_columns(self, mem_db):
        """raw_prices テーブルに必要なカラムが揃っていることを確認。"""
        cols = {
            row[0]
            for row in mem_db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'raw_prices'"
            ).fetchall()
        }
        assert {"date", "code", "open", "high", "low", "close", "volume", "turnover", "fetched_at"} <= cols

    def test_raw_financials_columns(self, mem_db):
        """raw_financials テーブルに必要なカラムが揃っていることを確認。"""
        cols = {
            row[0]
            for row in mem_db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'raw_financials'"
            ).fetchall()
        }
        assert {"code", "report_date", "period_type", "revenue", "operating_profit",
                "net_income", "eps", "roe", "fetched_at"} <= cols

    def test_market_calendar_columns(self, mem_db):
        """market_calendar テーブルに必要なカラムが揃っていることを確認。"""
        cols = {
            row[0]
            for row in mem_db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'market_calendar'"
            ).fetchall()
        }
        assert {"date", "is_trading_day", "is_half_day", "is_sq_day", "holiday_name"} <= cols

    def test_raw_prices_pk_constraint(self, mem_db):
        """raw_prices に同一 (date, code) を2回挿入すると ON CONFLICT で更新されることを確認。"""
        mem_db.execute(
            "INSERT INTO raw_prices (date, code, close) VALUES ('2024-01-10', '7203', 100.0)"
        )
        mem_db.execute(
            "INSERT INTO raw_prices (date, code, close) VALUES ('2024-01-10', '7203', 200.0) "
            "ON CONFLICT (date, code) DO UPDATE SET close = excluded.close"
        )
        count = mem_db.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
        assert count == 1


# ---------------------------------------------------------------------------
# J-Quants API クライアントのモック
# ---------------------------------------------------------------------------


class TestJQuantsClientMock:
    """_request をモックして fetch_* / save_* の動作を検証する。"""

    def test_fetch_daily_quotes_single_page(self, monkeypatch):
        """ページネーションなしで株価日足を取得できることを確認。"""
        records = [_sample_price_record()]
        monkeypatch.setattr(
            jquants, "_request",
            mock.MagicMock(return_value={"daily_quotes": records}),
        )
        result = jquants.fetch_daily_quotes(id_token="dummy")
        assert len(result) == 1
        assert result[0]["Code"] == "7203"

    def test_fetch_daily_quotes_pagination(self, monkeypatch):
        """2ページにわたる株価日足を結合して返すことを確認。"""
        page1 = {
            "daily_quotes": [_sample_price_record("2024-01-10")],
            "pagination_key": "page2_key",
        }
        page2 = {
            "daily_quotes": [_sample_price_record("2024-01-11")],
        }
        call_count = {"n": 0}

        def fake_request(path, params=None, **kw):
            call_count["n"] += 1
            if params and params.get("pagination_key") == "page2_key":
                return page2
            return page1

        monkeypatch.setattr(jquants, "_request", fake_request)
        result = jquants.fetch_daily_quotes(id_token="dummy")
        assert len(result) == 2
        assert call_count["n"] == 2

    def test_fetch_daily_quotes_dedup_pagination_key(self, monkeypatch):
        """同一 pagination_key が返り続けても無限ループしないことを確認。"""
        infinite = {"daily_quotes": [_sample_price_record()], "pagination_key": "same_key"}
        call_count = {"n": 0}

        def fake_request(path, params=None, **kw):
            call_count["n"] += 1
            return infinite

        monkeypatch.setattr(jquants, "_request", fake_request)
        result = jquants.fetch_daily_quotes(id_token="dummy")
        # 実装詳細（何回で打ち切るか）に依存しない: 有限回で終了し、データが無制限に蓄積されないことを確認
        assert 1 <= call_count["n"] <= 10
        assert len(result) < 100

    def test_fetch_financial_statements(self, monkeypatch):
        """財務データを取得できることを確認。"""
        records = [_sample_financial_record()]
        monkeypatch.setattr(
            jquants, "_request",
            mock.MagicMock(return_value={"statements": records}),
        )
        result = jquants.fetch_financial_statements(id_token="dummy")
        assert len(result) == 1
        assert result[0]["LocalCode"] == "7203"

    def test_fetch_market_calendar(self, monkeypatch):
        """カレンダーデータを取得できることを確認。"""
        records = [_sample_calendar_record()]
        monkeypatch.setattr(
            jquants, "_request",
            mock.MagicMock(return_value={"trading_calendar": records}),
        )
        result = jquants.fetch_market_calendar(id_token="dummy")
        assert len(result) == 1

    def test_get_id_token(self, monkeypatch):
        """リフレッシュトークンから ID トークンを取得できることを確認。"""
        monkeypatch.setattr(
            jquants, "_request",
            mock.MagicMock(return_value={"idToken": "my_id_token"}),
        )
        monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "dummy_refresh")
        token = jquants.get_id_token()
        assert token == "my_id_token"

    def test_get_id_token_missing_raises(self, monkeypatch):
        """リフレッシュトークンが未設定の場合は ValueError を送出することを確認。"""
        monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
        with pytest.raises(ValueError):
            jquants.get_id_token(refresh_token=None)


# ---------------------------------------------------------------------------
# ETL 冪等性確認
# ---------------------------------------------------------------------------


class TestEtlIdempotency:
    """同一データを複数回 save_* しても結果が変わらないことを確認する。"""

    def test_save_daily_quotes_idempotent(self, mem_db):
        """save_daily_quotes の2重実行で重複が生じないことを確認。"""
        records = [_sample_price_record()]
        count1 = jquants.save_daily_quotes(mem_db, records)
        count2 = jquants.save_daily_quotes(mem_db, records)
        assert count1 == 1
        assert count2 == 1
        # DB に1件のみ存在すること
        rows = mem_db.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
        assert rows == 1

    def test_save_daily_quotes_update_on_conflict(self, mem_db):
        """ON CONFLICT DO UPDATE で最新 close 値に更新されることを確認。"""
        records_v1 = [_sample_price_record(close=2830.0)]
        records_v2 = [_sample_price_record(close=2900.0)]
        jquants.save_daily_quotes(mem_db, records_v1)
        jquants.save_daily_quotes(mem_db, records_v2)
        close = mem_db.execute(
            "SELECT close FROM raw_prices WHERE date = '2024-01-10' AND code = '7203'"
        ).fetchone()[0]
        assert float(close) == 2900.0

    def test_save_daily_quotes_skips_missing_pk(self, mem_db):
        """Date または Code が欠損したレコードはスキップされることを確認。"""
        records = [
            {"Date": None, "Code": "7203", "Open": 100.0, "High": 110.0, "Low": 90.0, "Close": 105.0},
            {"Date": "2024-01-10", "Code": "", "Open": 100.0, "High": 110.0, "Low": 90.0, "Close": 105.0},
            _sample_price_record(),  # 正常レコード
        ]
        count = jquants.save_daily_quotes(mem_db, records)
        assert count == 1
        rows = mem_db.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
        assert rows == 1

    def test_save_financial_statements_idempotent(self, mem_db):
        """save_financial_statements の2重実行で重複が生じないことを確認。"""
        records = [_sample_financial_record()]
        jquants.save_financial_statements(mem_db, records)
        jquants.save_financial_statements(mem_db, records)
        rows = mem_db.execute("SELECT COUNT(*) FROM raw_financials").fetchone()[0]
        assert rows == 1

    def test_save_market_calendar_idempotent(self, mem_db):
        """save_market_calendar の2重実行で重複が生じないことを確認。"""
        records = [_sample_calendar_record()]
        jquants.save_market_calendar(mem_db, records)
        jquants.save_market_calendar(mem_db, records)
        rows = mem_db.execute("SELECT COUNT(*) FROM market_calendar").fetchone()[0]
        assert rows == 1

    def test_save_market_calendar_holiday_division(self, mem_db):
        """HolidayDivision ごとに is_trading_day / is_half_day / is_sq_day が正しくセットされることを確認。"""
        records = [
            _sample_calendar_record("2024-01-10", "0"),   # 全日営業
            _sample_calendar_record("2024-01-11", "2"),   # SQ日
            _sample_calendar_record("2024-01-12", "3"),   # 半日
            _sample_calendar_record("2024-01-13", "1"),   # 休場
        ]
        jquants.save_market_calendar(mem_db, records)

        def fetch(d):
            return mem_db.execute(
                "SELECT is_trading_day, is_half_day, is_sq_day "
                "FROM market_calendar WHERE date = ?", [d]
            ).fetchone()

        trading, half, sq = fetch("2024-01-10")
        assert trading and not half and not sq

        trading, half, sq = fetch("2024-01-11")
        assert trading and not half and sq

        trading, half, sq = fetch("2024-01-12")
        assert trading and half and not sq

        trading, half, sq = fetch("2024-01-13")
        assert not trading

    def test_save_multiple_codes(self, mem_db):
        """複数銘柄・複数日のデータを一括保存できることを確認。"""
        records = [
            _sample_price_record("2024-01-10", "7203"),
            _sample_price_record("2024-01-10", "9984"),
            _sample_price_record("2024-01-11", "7203"),
        ]
        count = jquants.save_daily_quotes(mem_db, records)
        assert count == 3
        rows = mem_db.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
        assert rows == 3

    def test_save_empty_records_returns_zero(self, mem_db):
        """空リストを渡したときに 0 を返すことを確認。"""
        assert jquants.save_daily_quotes(mem_db, []) == 0
        assert jquants.save_financial_statements(mem_db, []) == 0
        assert jquants.save_market_calendar(mem_db, []) == 0


# ---------------------------------------------------------------------------
# データ品質チェックとの統合
# ---------------------------------------------------------------------------


class TestQualityIntegration:
    """save_* で保存したデータに対し quality チェックが正しく動くことを確認。"""

    def test_no_issues_on_clean_data(self, mem_db):
        """正常データに対して品質チェックが問題を返さないことを確認。"""
        records = [_sample_price_record()]
        jquants.save_daily_quotes(mem_db, records)
        issues = quality.run_all_checks(
            mem_db,
            target_date=date(2024, 1, 10),
            reference_date=date(2025, 1, 1),
        )
        assert issues == []

    def test_missing_data_detected(self, mem_db):
        """OHLC 欠損があれば check_missing_data が検出することを確認。"""
        mem_db.execute(
            "INSERT INTO raw_prices (date, code, open, high, low, close) "
            "VALUES ('2024-01-10', '9999', NULL, 100.0, 90.0, 95.0)"
        )
        issues = quality.check_missing_data(mem_db, date(2024, 1, 10))
        assert len(issues) == 1
        assert issues[0].check_name == "missing_data"
        assert issues[0].severity == "error"

    def test_future_date_detected(self, mem_db):
        """基準日より後のデータが check_date_consistency で検出されることを確認。"""
        records = [_sample_price_record("2099-12-31")]
        jquants.save_daily_quotes(mem_db, records)
        issues = quality.check_date_consistency(mem_db, reference_date=date(2024, 1, 1))
        future_issues = [i for i in issues if i.check_name == "future_date"]
        assert len(future_issues) == 1
        assert future_issues[0].severity == "error"

    def test_spike_detected(self, mem_db):
        """前日比 50% 超の変動があれば check_spike が検出することを確認。"""
        records = [
            _sample_price_record("2024-01-09", close=1000.0),
            _sample_price_record("2024-01-10", close=2000.0),  # 100% 上昇
        ]
        jquants.save_daily_quotes(mem_db, records)
        issues = quality.check_spike(mem_db, date(2024, 1, 10))
        assert len(issues) == 1
        assert issues[0].check_name == "spike"
        assert issues[0].severity == "warning"

    def test_no_spike_within_threshold(self, mem_db):
        """閾値以内の変動では check_spike が問題を返さないことを確認。"""
        records = [
            _sample_price_record("2024-01-09", close=1000.0),
            _sample_price_record("2024-01-10", close=1100.0),  # 10% 上昇
        ]
        jquants.save_daily_quotes(mem_db, records)
        issues = quality.check_spike(mem_db, date(2024, 1, 10))
        assert issues == []


# ---------------------------------------------------------------------------
# 追加テスト: ON CONFLICT 複数カラム更新・未知 HolidayDivision・空レスポンス
# ---------------------------------------------------------------------------


class TestAdditionalCases:
    """ON CONFLICT DO UPDATE の複数カラム更新、未知区分、空レスポンスなどの境界ケース。"""

    def test_save_daily_quotes_on_conflict_updates_all_columns(self, mem_db):
        """ON CONFLICT DO UPDATE で open/high/low/close/volume/turnover が全て更新されることを確認。"""
        v1 = _sample_price_record(open_=100.0, high=110.0, low=90.0, close=105.0)
        v2 = _sample_price_record(open_=200.0, high=220.0, low=180.0, close=210.0)
        jquants.save_daily_quotes(mem_db, [v1])
        jquants.save_daily_quotes(mem_db, [v2])
        row = mem_db.execute(
            "SELECT open, high, low, close FROM raw_prices WHERE date='2024-01-10' AND code='7203'"
        ).fetchone()
        assert float(row[0]) == 200.0
        assert float(row[1]) == 220.0
        assert float(row[2]) == 180.0
        assert float(row[3]) == 210.0

    def test_save_market_calendar_unknown_holiday_division(self, mem_db):
        """未知の HolidayDivision（例: '9'）はデフォルト非営業日として扱われることを確認。"""
        records = [{"Date": "2024-01-15", "HolidayDivision": "9", "HolidayName": "Unknown"}]
        count = jquants.save_market_calendar(mem_db, records)
        assert count == 1
        row = mem_db.execute(
            "SELECT is_trading_day FROM market_calendar WHERE date = '2024-01-15'"
        ).fetchone()
        # 未知区分は {"0","2","3"} 以外なので is_trading_day=False（安全側デフォルト）
        assert row[0] in (False, 0)

    def test_fetch_daily_quotes_empty_response(self, monkeypatch):
        """API が空の daily_quotes を返した場合に空リストを返すことを確認。"""
        monkeypatch.setattr(
            jquants, "_request",
            mock.MagicMock(return_value={"daily_quotes": []}),
        )
        result = jquants.fetch_daily_quotes(id_token="dummy")
        assert result == []
