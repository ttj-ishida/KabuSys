"""イベントカレンダーパーサー。

config/event_calendar.md から FOMC・日銀・CPI 等の市場イベント日を読み込む。
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def load_event_dates(md_path: str | Path) -> dict[date, str]:
    """config/event_calendar.md をパースして {event_date: event_name} を返す。

    フォーマット:
        ### イベント名
        - YYYY-MM-DD

    ファイルが存在しない場合は空 dict を返す（安全側）。
    不正な日付行はスキップしてログを出力する。
    """
    path = Path(md_path)
    if not path.exists():
        logger.warning("load_event_dates: ファイルが見つかりません: %s", path)
        return {}

    text = path.read_text(encoding="utf-8")
    result: dict[date, str] = {}
    current_event = "event"

    for line in text.splitlines():
        m_header = re.match(r"^###\s+(.+)", line)
        if m_header:
            current_event = m_header.group(1).strip()
            continue

        m_date = re.match(r"^-\s+(\d{4}-\d{2}-\d{2})\s*$", line)
        if m_date:
            try:
                d = date.fromisoformat(m_date.group(1))
                if d in result:
                    logger.warning(
                        "load_event_dates: 日付 %s が複数イベントに登録されています "
                        "('%s' → '%s')。後者で上書きします。",
                        d, result[d], current_event,
                    )
                result[d] = current_event
            except ValueError:
                logger.debug("load_event_dates: 不正な日付 '%s'—スキップ", m_date.group(1))

    logger.info("load_event_dates: %d 件のイベント日を読み込み: %s", len(result), path)
    return result
