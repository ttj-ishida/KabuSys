"""
news_collector モジュールのユニットテスト

fetch_rss / preprocess_text / save_raw_news / extract_stock_codes /
save_news_symbols / run_news_collection の動作を検証する。
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import duckdb
import pytest

from kabusys.data.news_collector import (
    DEFAULT_RSS_SOURCES,
    _make_article_id,
    _parse_rss_datetime,
    extract_stock_codes,
    fetch_rss,
    preprocess_text,
    run_news_collection,
    save_news_symbols,
    save_raw_news,
)

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

_NEWS_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_news (
        id          VARCHAR     NOT NULL PRIMARY KEY,
        datetime    TIMESTAMP   NOT NULL,
        source      VARCHAR     NOT NULL,
        title       VARCHAR,
        content     VARCHAR,
        url         VARCHAR,
        fetched_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news_articles (
        id          VARCHAR     NOT NULL PRIMARY KEY,
        datetime    TIMESTAMP   NOT NULL,
        source      VARCHAR     NOT NULL,
        title       VARCHAR,
        content     VARCHAR,
        url         VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news_symbols (
        news_id     VARCHAR     NOT NULL,
        code        VARCHAR     NOT NULL,
        PRIMARY KEY (news_id, code)
    )
    """,
]


@pytest.fixture
def news_db():
    conn = duckdb.connect(":memory:")
    for ddl in _NEWS_DDL:
        conn.execute(ddl)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# ユーティリティテスト
# ---------------------------------------------------------------------------


def test_make_article_id_deterministic():
    url = "https://example.com/article/1"
    assert _make_article_id(url) == _make_article_id(url)
    assert len(_make_article_id(url)) == 16


def test_make_article_id_different_urls():
    assert _make_article_id("https://a.com/1") != _make_article_id("https://a.com/2")


def test_preprocess_text_removes_urls():
    text = "トヨタ https://example.com/news 急騰"
    assert "https://" not in preprocess_text(text)
    assert "トヨタ" in preprocess_text(text)
    assert "急騰" in preprocess_text(text)


def test_preprocess_text_normalizes_whitespace():
    assert preprocess_text("  hello   world  ") == "hello world"
    assert preprocess_text("line1\n\nline2") == "line1 line2"


def test_preprocess_text_none_returns_empty():
    assert preprocess_text(None) == ""
    assert preprocess_text("") == ""


def test_parse_rss_datetime_rfc2822():
    dt = _parse_rss_datetime("Mon, 01 Jan 2024 12:00:00 +0900")
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 3  # +0900 -> UTC: 12:00 - 9:00 = 03:00
    assert dt.tzinfo is None  # naive UTC


def test_parse_rss_datetime_invalid_returns_now():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    dt = _parse_rss_datetime("not a date")
    after = datetime.now(timezone.utc).replace(tzinfo=None)
    assert before <= dt <= after


def test_parse_rss_datetime_none_returns_now():
    dt = _parse_rss_datetime(None)
    assert isinstance(dt, datetime)


# ---------------------------------------------------------------------------
# fetch_rss テスト
# ---------------------------------------------------------------------------

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test News</title>
    <item>
      <title>Toyota 7203 surge</title>
      <link>https://news.example.com/article/1</link>
      <description>Article body https://remove.me/link</description>
      <pubDate>Mon, 15 Jan 2024 09:00:00 +0900</pubDate>
    </item>
    <item>
      <title>Sony earnings 6758</title>
      <link>https://news.example.com/article/2</link>
      <description>Sony Group 6758 earnings announcement</description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 +0900</pubDate>
    </item>
    <item>
      <link></link>
      <title>No link item (should be skipped)</title>
    </item>
  </channel>
</rss>""".encode("utf-8")


class _MockResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_fetch_rss_parses_items(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=30: _MockResponse(_SAMPLE_RSS),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert len(articles) == 2
    assert articles[0]["source"] == "test"
    assert articles[0]["title"] == "Toyota 7203 surge"
    assert "https://" not in articles[0]["content"]
    assert articles[0]["url"] == "https://news.example.com/article/1"
    assert len(articles[0]["id"]) == 16


def test_fetch_rss_skips_items_without_link(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=30: _MockResponse(_SAMPLE_RSS),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    urls = [a["url"] for a in articles]
    assert all(u for u in urls)


def test_fetch_rss_no_channel(monkeypatch):
    no_channel_rss = b"<?xml version='1.0'?><rss><title>X</title></rss>"
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=30: _MockResponse(no_channel_rss),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert articles == []


# ---------------------------------------------------------------------------
# save_raw_news テスト
# ---------------------------------------------------------------------------


def _make_article(idx: int = 1) -> dict:
    url = f"https://news.example.com/article/{idx}"
    return {
        "id": _make_article_id(url),
        "datetime": datetime(2024, 1, 15, 9, 0, 0),
        "source": "test",
        "title": f"テスト記事{idx}",
        "content": "本文テキスト",
        "url": url,
    }


def test_save_raw_news_basic(news_db):
    articles = [_make_article(1), _make_article(2)]
    saved = save_raw_news(news_db, articles)
    assert saved == 2
    count = news_db.execute("SELECT COUNT(*) FROM raw_news").fetchone()[0]
    assert count == 2


def test_save_raw_news_idempotent(news_db):
    art = _make_article(1)
    save_raw_news(news_db, [art])
    saved2 = save_raw_news(news_db, [art])
    # ON CONFLICT DO NOTHING: 2回目もカウントされるが重複挿入はされない
    count = news_db.execute("SELECT COUNT(*) FROM raw_news").fetchone()[0]
    assert count == 1


def test_save_raw_news_skips_missing_id(news_db):
    articles = [{"id": "", "datetime": datetime.now(), "source": "x", "title": "t", "content": "", "url": "u"}]
    saved = save_raw_news(news_db, articles)
    assert saved == 0


def test_save_raw_news_empty(news_db):
    assert save_raw_news(news_db, []) == 0


# ---------------------------------------------------------------------------
# extract_stock_codes テスト
# ---------------------------------------------------------------------------


def test_extract_stock_codes_finds_known_codes():
    codes = extract_stock_codes("トヨタ 7203 が急騰、ソニー 6758 も上昇", {"7203", "6758", "9999"})
    assert "7203" in codes
    assert "6758" in codes


def test_extract_stock_codes_ignores_unknown_codes():
    codes = extract_stock_codes("1234 という数字がある", {"7203"})
    assert codes == []


def test_extract_stock_codes_deduplicates():
    codes = extract_stock_codes("7203 と 7203 が二度登場", {"7203"})
    assert codes.count("7203") == 1


def test_extract_stock_codes_empty_text():
    assert extract_stock_codes("", {"7203"}) == []


def test_extract_stock_codes_no_known_codes():
    assert extract_stock_codes("7203 が上昇", set()) == []


# ---------------------------------------------------------------------------
# save_news_symbols テスト
# ---------------------------------------------------------------------------


def test_save_news_symbols_basic(news_db):
    art = _make_article(1)
    save_raw_news(news_db, [art])
    saved = save_news_symbols(news_db, art["id"], ["7203", "6758"])
    assert saved == 2
    count = news_db.execute("SELECT COUNT(*) FROM news_symbols").fetchone()[0]
    assert count == 2


def test_save_news_symbols_idempotent(news_db):
    art = _make_article(1)
    save_raw_news(news_db, [art])
    save_news_symbols(news_db, art["id"], ["7203"])
    save_news_symbols(news_db, art["id"], ["7203"])
    count = news_db.execute("SELECT COUNT(*) FROM news_symbols").fetchone()[0]
    assert count == 1


def test_save_news_symbols_empty(news_db):
    assert save_news_symbols(news_db, "x", []) == 0


# ---------------------------------------------------------------------------
# run_news_collection テスト
# ---------------------------------------------------------------------------


def test_run_news_collection_uses_default_sources(monkeypatch, news_db):
    captured = {}

    def fake_fetch_rss(url, source, timeout=30):
        captured[source] = url
        return [_make_article(1)]

    monkeypatch.setattr("kabusys.data.news_collector.fetch_rss", fake_fetch_rss)
    monkeypatch.setattr("kabusys.data.news_collector.save_raw_news", lambda conn, arts: 1)

    results = run_news_collection(news_db)
    assert set(results.keys()) == set(DEFAULT_RSS_SOURCES.keys())


def test_run_news_collection_custom_sources(monkeypatch, news_db):
    monkeypatch.setattr(
        "kabusys.data.news_collector.fetch_rss",
        lambda url, source, timeout=30: [_make_article(1)],
    )
    results = run_news_collection(
        news_db,
        sources={"custom_src": "https://custom.rss"},
    )
    assert "custom_src" in results


def test_run_news_collection_error_continues(monkeypatch, news_db):
    import urllib.error

    def fail_fetch(url, source, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("kabusys.data.news_collector.fetch_rss", fail_fetch)
    results = run_news_collection(
        news_db, sources={"src1": "https://fail.rss", "src2": "https://also-fail.rss"}
    )
    assert results == {"src1": 0, "src2": 0}


def test_run_news_collection_extracts_symbols(monkeypatch, news_db):
    art = _make_article(1)
    art["title"] = "トヨタ 7203 が急騰"
    art["content"] = "ソニー 6758 も上昇"

    monkeypatch.setattr(
        "kabusys.data.news_collector.fetch_rss",
        lambda url, source, timeout=30: [art],
    )
    run_news_collection(
        news_db,
        sources={"src": "https://dummy.rss"},
        known_codes={"7203", "6758"},
    )
    count = news_db.execute("SELECT COUNT(*) FROM news_symbols").fetchone()[0]
    assert count == 2
