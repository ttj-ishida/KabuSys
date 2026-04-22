"""event_calendar.py のユニットテスト。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def sample_md(tmp_path: Path) -> Path:
    md = tmp_path / "event_calendar.md"
    md.write_text(
        "## 2026年\n\n"
        "### FOMC\n"
        "- 2026-01-29\n"
        "- 2026-03-19\n\n"
        "### 日銀決定会合\n"
        "- 2026-01-24\n\n"
        "### 米CPI\n"
        "- 2026-01-15\n",
        encoding="utf-8",
    )
    return md


def test_load_event_dates_parses_all_dates(sample_md):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(sample_md)
    assert date(2026, 1, 29) in result
    assert date(2026, 3, 19) in result
    assert date(2026, 1, 24) in result
    assert date(2026, 1, 15) in result


def test_load_event_dates_returns_event_name(sample_md):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(sample_md)
    assert result[date(2026, 1, 29)] == "FOMC"
    assert result[date(2026, 1, 24)] == "日銀決定会合"
    assert result[date(2026, 1, 15)] == "米CPI"


def test_load_event_dates_missing_file_returns_empty(tmp_path):
    from kabusys.data.event_calendar import load_event_dates

    result = load_event_dates(tmp_path / "nonexistent.md")
    assert result == {}


def test_load_event_dates_ignores_malformed_lines(tmp_path):
    from kabusys.data.event_calendar import load_event_dates

    md = tmp_path / "bad.md"
    md.write_text("### FOMC\n- not-a-date\n- 2026-02-01\n", encoding="utf-8")
    result = load_event_dates(md)
    assert date(2026, 2, 1) in result
    assert len(result) == 1


def test_load_event_dates_duplicate_date_last_wins(tmp_path):
    """同一日が複数イベントに登録された場合、後のセクションで上書きされる。"""
    from kabusys.data.event_calendar import load_event_dates

    md = tmp_path / "dup.md"
    md.write_text(
        "### FOMC\n- 2026-03-19\n\n### 日銀決定会合\n- 2026-03-19\n",
        encoding="utf-8",
    )
    result = load_event_dates(md)
    assert date(2026, 3, 19) in result
    assert len(result) == 1
    assert result[date(2026, 3, 19)] == "日銀決定会合"
