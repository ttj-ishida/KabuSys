# src/kabusys/utils/datetime_utils.py
"""日時ユーティリティ。表示層での UTC → JST 変換に使用する。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    _JST = ZoneInfo("Asia/Tokyo")
except Exception:
    _JST = timezone(timedelta(hours=9))  # tzdata 未インストール環境向けフォールバック


def to_jst_str(iso_utc: str | datetime | None) -> str:
    """UTC ISO 文字列を JST 表示文字列に変換する。

    - 'Z' 末尾の文字列は '+00:00' に正規化する（Python 3.10 互換）。
    - datetime オブジェクトはそのまま変換する。
    - タイムゾーン情報なし（naive）の文字列・datetime は UTC として扱う。
    - None または空文字列は 'N/A' を返す。
    - パース失敗時は元の値を文字列化して返す（表示が壊れない）。

    返り値フォーマット: "YYYY-MM-DD HH:MM:SS JST"
    """
    if iso_utc is None or iso_utc == "":
        return "N/A"
    try:
        if isinstance(iso_utc, datetime):
            dt = iso_utc
        else:
            s = str(iso_utc).strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_JST).strftime("%Y-%m-%d %H:%M:%S JST")
    except (ValueError, TypeError, AttributeError):
        return str(iso_utc)
