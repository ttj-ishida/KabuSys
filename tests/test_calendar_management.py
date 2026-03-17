"""
calendar_management モジュールのユニットテスト

テスト方針:
  - インメモリ DuckDB（tests/conftest.py の mem_db フィクスチャ）を使用
  - J-Quants API 呼び出し（jq.fetch_market_calendar / jq.save_market_calendar）は
    monkeypatch でモック化し、外部通信なしでテストする
  - テスト用カレンダーデータは直接 INSERT して用意する
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data import calendar_management as cm


# ---------------------------------------------------------------------------
# ヘルパー: テスト用カレンダーデータ挿入
# ---------------------------------------------------------------------------

def _insert_calendar(conn, rows: list[dict]) -> None:
    """market_calendar に rows をまとめて INSERT する。"""
    for r in rows:
        conn.execute(
            """
            INSERT INTO market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                is_trading_day = excluded.is_trading_day,
                is_half_day    = excluded.is_half_day,
                is_sq_day      = excluded.is_sq_day,
                holiday_name   = excluded.holiday_name
            """,
            [
                r["date"],
                r.get("is_trading_day", True),
                r.get("is_half_day", False),
                r.get("is_sq_day", False),
                r.get("holiday_name"),
            ],
        )


# ---------------------------------------------------------------------------
# _table_exists
# ---------------------------------------------------------------------------

class TestTableExists:
    def test_existing_table_returns_true(self, mem_db):
        assert cm._table_exists(mem_db, "market_calendar") is True

    def test_missing_table_returns_false(self, mem_db):
        assert cm._table_exists(mem_db, "nonexistent_table") is False


# ---------------------------------------------------------------------------
# _has_calendar_data
# ---------------------------------------------------------------------------

class TestHasCalendarData:
    def test_empty_table_returns_false(self, mem_db):
        assert cm._has_calendar_data(mem_db) is False

    def test_with_data_returns_true(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 1, 6), "is_trading_day": True}])
        assert cm._has_calendar_data(mem_db) is True


# ---------------------------------------------------------------------------
# _is_weekend
# ---------------------------------------------------------------------------

class TestIsWeekend:
    def test_monday_is_not_weekend(self):
        assert cm._is_weekend(date(2025, 1, 6)) is False  # 月曜日

    def test_friday_is_not_weekend(self):
        assert cm._is_weekend(date(2025, 1, 10)) is False  # 金曜日

    def test_saturday_is_weekend(self):
        assert cm._is_weekend(date(2025, 1, 11)) is True  # 土曜日

    def test_sunday_is_weekend(self):
        assert cm._is_weekend(date(2025, 1, 12)) is True  # 日曜日


# ---------------------------------------------------------------------------
# is_trading_day
# ---------------------------------------------------------------------------

class TestIsTradingDay:
    def test_returns_true_for_trading_day_in_db(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 1, 6), "is_trading_day": True}])
        assert cm.is_trading_day(mem_db, date(2025, 1, 6)) is True

    def test_returns_false_for_holiday_in_db(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 1, 1), "is_trading_day": False, "holiday_name": "元日"}])
        assert cm.is_trading_day(mem_db, date(2025, 1, 1)) is False

    def test_fallback_weekday_when_no_db(self, mem_db):
        # テーブルにデータなし → 曜日フォールバック
        assert cm.is_trading_day(mem_db, date(2025, 1, 6)) is True   # 月曜日

    def test_fallback_weekend_when_no_db(self, mem_db):
        assert cm.is_trading_day(mem_db, date(2025, 1, 11)) is False  # 土曜日

    def test_fallback_weekday_when_date_out_of_db_range(self, mem_db):
        # DB には 2025-01-06 のみ存在、範囲外の 2025-02-01 は曜日フォールバック
        _insert_calendar(mem_db, [{"date": date(2025, 1, 6), "is_trading_day": True}])
        assert cm.is_trading_day(mem_db, date(2025, 2, 1)) is False   # 土曜日（フォールバック）

    def test_fallback_weekday_out_of_range_weekday(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 1, 6), "is_trading_day": True}])
        assert cm.is_trading_day(mem_db, date(2025, 2, 3)) is True   # 月曜日（フォールバック）


# ---------------------------------------------------------------------------
# is_sq_day
# ---------------------------------------------------------------------------

class TestIsSqDay:
    def test_returns_true_for_sq_day(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 3, 14), "is_trading_day": True, "is_sq_day": True}])
        assert cm.is_sq_day(mem_db, date(2025, 3, 14)) is True

    def test_returns_false_for_non_sq_day(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 3, 13), "is_trading_day": True, "is_sq_day": False}])
        assert cm.is_sq_day(mem_db, date(2025, 3, 13)) is False

    def test_returns_false_when_no_db_data(self, mem_db):
        assert cm.is_sq_day(mem_db, date(2025, 3, 14)) is False

    def test_returns_false_when_date_not_in_db(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 3, 14), "is_trading_day": True, "is_sq_day": True}])
        assert cm.is_sq_day(mem_db, date(2025, 3, 15)) is False


# ---------------------------------------------------------------------------
# next_trading_day
# ---------------------------------------------------------------------------

class TestNextTradingDay:
    def test_next_day_is_trading(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": True},
        ])
        assert cm.next_trading_day(mem_db, date(2025, 1, 6)) == date(2025, 1, 7)

    def test_skips_holiday(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "祝日"},
            {"date": date(2025, 1, 8), "is_trading_day": True},
        ])
        assert cm.next_trading_day(mem_db, date(2025, 1, 6)) == date(2025, 1, 8)

    def test_fallback_skips_weekend(self, mem_db):
        # テーブルにデータなし → 曜日フォールバック
        # 2025-01-10 (金) → 翌営業日は 2025-01-13 (月)
        assert cm.next_trading_day(mem_db, date(2025, 1, 10)) == date(2025, 1, 13)

    def test_raises_when_no_trading_day_found(self, mem_db, monkeypatch):
        # _is_weekend が常に True を返す（全日が週末扱い）→ フォールバックでも見つからない
        monkeypatch.setattr(cm, "_is_weekend", lambda d: True)
        with pytest.raises(ValueError, match="営業日が見つかりません"):
            cm.next_trading_day(mem_db, date(2025, 1, 1))

    def test_does_not_return_same_day(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": True},
        ])
        result = cm.next_trading_day(mem_db, date(2025, 1, 6))
        assert result > date(2025, 1, 6)

    def test_skips_registered_holiday_in_sparse_db(self, mem_db):
        """DB がまばらで休日のみ登録されている場合、登録済み休日を正しくスキップする。"""
        # 2025-01-08（水）が休日として登録、他は未登録
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 8), "is_trading_day": False, "holiday_name": "振替休日"},
        ])
        # DB に 2025-01-07 は未登録 → 曜日フォールバック（火曜=平日）で返すべき
        result = cm.next_trading_day(mem_db, date(2025, 1, 6))
        assert result == date(2025, 1, 7)

    def test_skips_registered_holiday_then_falls_back(self, mem_db):
        """登録済み休日の翌日が未登録の平日 → フォールバックで返す。"""
        # 2025-01-07（火）が休日として登録
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "祝日"},
        ])
        # 2025-01-07 はスキップ → 2025-01-08（水）は未登録=曜日フォールバック（平日）
        result = cm.next_trading_day(mem_db, date(2025, 1, 6))
        assert result == date(2025, 1, 8)


# ---------------------------------------------------------------------------
# prev_trading_day
# ---------------------------------------------------------------------------

class TestPrevTradingDay:
    def test_prev_day_is_trading(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": True},
        ])
        assert cm.prev_trading_day(mem_db, date(2025, 1, 7)) == date(2025, 1, 6)

    def test_skips_holiday(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "祝日"},
            {"date": date(2025, 1, 8), "is_trading_day": True},
        ])
        assert cm.prev_trading_day(mem_db, date(2025, 1, 8)) == date(2025, 1, 6)

    def test_fallback_skips_weekend(self, mem_db):
        # テーブルにデータなし → 曜日フォールバック
        # 2025-01-13 (月) → 前営業日は 2025-01-10 (金)
        assert cm.prev_trading_day(mem_db, date(2025, 1, 13)) == date(2025, 1, 10)

    def test_raises_when_no_trading_day_found(self, mem_db, monkeypatch):
        # _is_weekend が常に True を返す（全日が週末扱い）→ フォールバックでも見つからない
        monkeypatch.setattr(cm, "_is_weekend", lambda d: True)
        with pytest.raises(ValueError, match="営業日が見つかりません"):
            cm.prev_trading_day(mem_db, date(2025, 1, 31))

    def test_does_not_return_same_day(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": True},
        ])
        result = cm.prev_trading_day(mem_db, date(2025, 1, 7))
        assert result < date(2025, 1, 7)

    def test_skips_registered_holiday_in_sparse_db(self, mem_db):
        """DB がまばらで休日のみ登録されている場合、登録済み休日を正しくスキップする。"""
        # 2025-01-07（火）が休日として登録、他は未登録
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "振替休日"},
        ])
        # DB に 2025-01-06 は未登録 → 曜日フォールバック（月曜=平日）で返すべき
        result = cm.prev_trading_day(mem_db, date(2025, 1, 8))
        assert result == date(2025, 1, 6)

    def test_skips_registered_holiday_then_falls_back(self, mem_db):
        """登録済み休日の前日が未登録の平日 → フォールバックで返す。"""
        # 2025-01-07（火）が休日として登録
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "祝日"},
        ])
        # 2025-01-07 はスキップ → 2025-01-06（月）は未登録=曜日フォールバック（平日）
        result = cm.prev_trading_day(mem_db, date(2025, 1, 8))
        assert result == date(2025, 1, 6)


# ---------------------------------------------------------------------------
# get_trading_days
# ---------------------------------------------------------------------------

class TestGetTradingDays:
    def test_empty_when_start_after_end(self, mem_db):
        assert cm.get_trading_days(mem_db, date(2025, 1, 10), date(2025, 1, 5)) == []

    def test_single_trading_day(self, mem_db):
        _insert_calendar(mem_db, [{"date": date(2025, 1, 6), "is_trading_day": True}])
        result = cm.get_trading_days(mem_db, date(2025, 1, 6), date(2025, 1, 6))
        assert result == [date(2025, 1, 6)]

    def test_excludes_holidays(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": False, "holiday_name": "祝日"},
            {"date": date(2025, 1, 8), "is_trading_day": True},
        ])
        result = cm.get_trading_days(mem_db, date(2025, 1, 6), date(2025, 1, 8))
        assert result == [date(2025, 1, 6), date(2025, 1, 8)]

    def test_fallback_excludes_weekends(self, mem_db):
        # テーブルにデータなし → 曜日フォールバック（2025-01-06 月 〜 01-10 金）
        result = cm.get_trading_days(mem_db, date(2025, 1, 6), date(2025, 1, 12))
        assert date(2025, 1, 11) not in result  # 土
        assert date(2025, 1, 12) not in result  # 日
        assert date(2025, 1, 6) in result       # 月
        assert date(2025, 1, 10) in result      # 金

    def test_result_is_sorted_ascending(self, mem_db):
        _insert_calendar(mem_db, [
            {"date": date(2025, 1, 6), "is_trading_day": True},
            {"date": date(2025, 1, 7), "is_trading_day": True},
            {"date": date(2025, 1, 8), "is_trading_day": True},
        ])
        result = cm.get_trading_days(mem_db, date(2025, 1, 6), date(2025, 1, 8))
        assert result == sorted(result)

    def test_range_before_db_coverage_uses_fallback(self, mem_db):
        # DB のカバレッジ: 2025-01-13 のみ
        _insert_calendar(mem_db, [{"date": date(2025, 1, 13), "is_trading_day": True}])
        # 2025-01-10 (金) はカレンダー前 → 曜日フォールバック
        result = cm.get_trading_days(mem_db, date(2025, 1, 10), date(2025, 1, 13))
        assert date(2025, 1, 10) in result  # 金曜（フォールバックで追加）
        assert date(2025, 1, 13) in result  # DB から

    def test_range_after_db_coverage_uses_fallback(self, mem_db):
        # DB のカバレッジ: 2025-01-13 のみ
        _insert_calendar(mem_db, [{"date": date(2025, 1, 13), "is_trading_day": True}])
        # 2025-01-14 以降はカレンダー後 → 曜日フォールバック
        result = cm.get_trading_days(mem_db, date(2025, 1, 13), date(2025, 1, 17))
        assert date(2025, 1, 13) in result  # DB から（月曜）
        assert date(2025, 1, 14) in result  # 火（フォールバック）
        assert date(2025, 1, 17) in result  # 金（フォールバック）

    def test_no_duplicates_when_boundary_overlaps(self, mem_db):
        # DB に 2025-01-13 あり、範囲外補完と重複しないことを確認
        _insert_calendar(mem_db, [{"date": date(2025, 1, 13), "is_trading_day": True}])
        result = cm.get_trading_days(mem_db, date(2025, 1, 13), date(2025, 1, 14))
        assert result.count(date(2025, 1, 13)) == 1


# ---------------------------------------------------------------------------
# calendar_update_job
# ---------------------------------------------------------------------------

class TestCalendarUpdateJob:
    def test_returns_zero_when_already_up_to_date(self, mem_db, monkeypatch):
        import kabusys.data.jquants_client as jq
        # 今日から 200 日先まで登録済みにしておけばデフォルト lookahead (90日) を上回る
        far_future = date.today() + timedelta(days=200)
        _insert_calendar(mem_db, [{"date": far_future, "is_trading_day": True}])

        fetch_called = []
        monkeypatch.setattr(jq, "fetch_market_calendar", lambda **kw: fetch_called.append(kw) or [])
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: 0)

        result = cm.calendar_update_job(mem_db)
        assert result == 0
        assert fetch_called == []  # 最新なので fetch は呼ばれない

    def test_fetches_and_saves_records(self, mem_db, monkeypatch):
        import kabusys.data.jquants_client as jq

        fake_records = [
            {"Date": "2025-03-18", "TradingDay": True, "HalfDay": False, "SQDay": False},
        ]
        monkeypatch.setattr(jq, "fetch_market_calendar", lambda **kw: fake_records)
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: len(recs))

        result = cm.calendar_update_job(mem_db)
        assert result == 1

    def test_returns_zero_when_no_records_fetched(self, mem_db, monkeypatch):
        import kabusys.data.jquants_client as jq

        monkeypatch.setattr(jq, "fetch_market_calendar", lambda **kw: [])
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: 0)

        result = cm.calendar_update_job(mem_db)
        assert result == 0

    def test_date_from_is_after_last_saved(self, mem_db, monkeypatch):
        """差分取得: 既存最終日の翌日から取得することを確認する。"""
        import kabusys.data.jquants_client as jq

        last_saved = date(2025, 3, 10)
        _insert_calendar(mem_db, [{"date": last_saved, "is_trading_day": True}])

        captured = {}

        def fake_fetch(*, date_from, date_to):
            captured["date_from"] = date_from
            return []

        monkeypatch.setattr(jq, "fetch_market_calendar", fake_fetch)
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: 0)

        cm.calendar_update_job(mem_db)
        assert captured["date_from"] == (last_saved + timedelta(days=1)).isoformat()

    def test_returns_zero_when_fetch_raises(self, mem_db, monkeypatch):
        """fetch_market_calendar が例外を送出しても 0 を返す。"""
        import kabusys.data.jquants_client as jq

        def bad_fetch(**kw):
            raise RuntimeError("API 接続失敗")

        monkeypatch.setattr(jq, "fetch_market_calendar", bad_fetch)
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: 0)

        result = cm.calendar_update_job(mem_db)
        assert result == 0

    def test_returns_zero_when_save_raises(self, mem_db, monkeypatch):
        """save_market_calendar が例外を送出しても 0 を返す。"""
        import kabusys.data.jquants_client as jq

        fake_records = [
            {"Date": "2025-03-18", "TradingDay": True, "HalfDay": False, "SQDay": False},
        ]
        monkeypatch.setattr(jq, "fetch_market_calendar", lambda **kw: fake_records)
        monkeypatch.setattr(jq, "save_market_calendar", lambda conn, recs: (_ for _ in ()).throw(RuntimeError("DB 保存失敗")))

        result = cm.calendar_update_job(mem_db)
        assert result == 0
