# tests/test_datetime_utils.py
"""to_jst_str のユニットテスト。"""

from __future__ import annotations

from kabusys.utils.datetime_utils import to_jst_str


class TestToJstStr:
    def test_utc_offset_string(self):
        """UTC+00:00 の ISO 文字列を JST に変換する。"""
        assert to_jst_str("2026-05-13T06:00:00+00:00") == "2026-05-13 15:00:00 JST"

    def test_utc_z_suffix(self):
        """Z 末尾の UTC 文字列を JST に変換する。"""
        assert to_jst_str("2026-05-13T06:00:00Z") == "2026-05-13 15:00:00 JST"

    def test_midnight_utc_crosses_date(self):
        """UTC 00:00 は JST 09:00（日付変わらず）。"""
        assert to_jst_str("2026-05-13T00:00:00+00:00") == "2026-05-13 09:00:00 JST"

    def test_utc_1500_crosses_midnight(self):
        """UTC 15:00 は JST 翌日 00:00（日付が変わる）。"""
        assert to_jst_str("2026-05-13T15:00:00+00:00") == "2026-05-14 00:00:00 JST"

    def test_naive_datetime_treated_as_utc(self):
        """タイムゾーン情報なしの文字列は UTC として扱う。"""
        assert to_jst_str("2026-05-13T06:00:00") == "2026-05-13 15:00:00 JST"

    def test_none_returns_na(self):
        """None を渡すと 'N/A' を返す。"""
        assert to_jst_str(None) == "N/A"

    def test_empty_string_returns_na(self):
        """空文字列を渡すと 'N/A' を返す。"""
        assert to_jst_str("") == "N/A"

    def test_truncated_19char_string(self):
        """[:19] でタイムゾーンが切り落とされた文字列（naive）も UTC として扱う。"""
        assert to_jst_str("2026-05-13T06:00:00") == "2026-05-13 15:00:00 JST"

    def test_invalid_string_returns_original(self):
        """パース不能な文字列はそのまま返す（表示が壊れない）。"""
        assert to_jst_str("not-a-datetime") == "not-a-datetime"
