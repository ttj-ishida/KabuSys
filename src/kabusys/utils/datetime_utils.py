# src/kabusys/utils/datetime_utils.py
"""日時ユーティリティ。表示層での UTC → JST 変換に使用する。"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_JST = ZoneInfo("Asia/Tokyo")


def to_jst_str(iso_utc: str | None) -> str:
    """UTC ISO 文字列を JST 表示文字列に変換する。

    - タイムゾーン情報なし（naive）の文字列は UTC として扱う。
    - None または空文字列は 'N/A' を返す。
    - パース失敗時は元の文字列をそのまま返す（表示が壊れない）。

    返り値フォーマット: "YYYY-MM-DD HH:MM:SS JST"
    """
    if not iso_utc:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_JST).strftime("%Y-%m-%d %H:%M:%S JST")
    except (ValueError, TypeError):
        return iso_utc
