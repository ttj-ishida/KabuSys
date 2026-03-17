"""
news_collector モジュールのユニットテスト
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock
import urllib.error

import duckdb
import pytest

from kabusys.data.news_collector import (
    DEFAULT_RSS_SOURCES,
    _make_article_id,
    _normalize_url,
    _parse_rss_datetime,
    _validate_url_scheme,
    extract_stock_codes,
    fetch_rss,
    preprocess_text,
    run_news_collection,
    save_news_symbols,
    save_raw_news,
)

# ---------------------------------------------------------------------------
# フィクスチャ（news_articles DDL は使用しないため除外）
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
# URL正規化・ID生成テスト
# ---------------------------------------------------------------------------


def test_normalize_url_removes_tracking_params():
    url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=1"
    normalized = _normalize_url(url)
    assert "utm_source" not in normalized
    assert "id=1" in normalized


def test_normalize_url_removes_fragment():
    url = "https://example.com/article#section1"
    assert "#" not in _normalize_url(url)


def test_normalize_url_sorts_query_params():
    url1 = "https://example.com/?b=2&a=1"
    url2 = "https://example.com/?a=1&b=2"
    assert _normalize_url(url1) == _normalize_url(url2)


def test_normalize_url_lowercases_scheme_and_host():
    url = "HTTPS://Example.COM/path"
    normalized = _normalize_url(url)
    assert normalized.startswith("https://example.com/")


def test_make_article_id_deterministic():
    url = "https://example.com/article/1"
    assert _make_article_id(url) == _make_article_id(url)
    assert len(_make_article_id(url)) == 32


def test_make_article_id_ignores_tracking_params():
    url1 = "https://example.com/article?id=1"
    url2 = "https://example.com/article?id=1&utm_source=twitter"
    assert _make_article_id(url1) == _make_article_id(url2)


def test_make_article_id_different_for_different_urls():
    assert _make_article_id("https://a.com/1") != _make_article_id("https://a.com/2")


# ---------------------------------------------------------------------------
# URLスキーム検証テスト
# ---------------------------------------------------------------------------


def test_validate_url_scheme_accepts_http():
    _validate_url_scheme("http://example.com/feed.rss")  # no exception


def test_validate_url_scheme_accepts_https():
    _validate_url_scheme("https://example.com/feed.rss")  # no exception


def test_validate_url_scheme_rejects_file():
    with pytest.raises(ValueError, match="file"):
        _validate_url_scheme("file:///etc/passwd")


def test_validate_url_scheme_rejects_ftp():
    with pytest.raises(ValueError):
        _validate_url_scheme("ftp://example.com/feed.rss")


# ---------------------------------------------------------------------------
# テキスト前処理テスト
# ---------------------------------------------------------------------------


def test_preprocess_text_removes_urls():
    text = "Stock surge https://example.com/news details"
    assert "https://" not in preprocess_text(text)
    assert "Stock surge" in preprocess_text(text)
    assert "details" in preprocess_text(text)


def test_preprocess_text_normalizes_whitespace():
    assert preprocess_text("  hello   world  ") == "hello world"
    assert preprocess_text("line1\n\nline2") == "line1 line2"


def test_preprocess_text_none_returns_empty():
    assert preprocess_text(None) == ""
    assert preprocess_text("") == ""


# ---------------------------------------------------------------------------
# 日時パーステスト
# ---------------------------------------------------------------------------


def test_parse_rss_datetime_rfc2822():
    dt = _parse_rss_datetime("Mon, 01 Jan 2024 12:00:00 +0900")
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 3  # +0900 -> UTC: 12:00 - 9:00 = 03:00
    assert dt.tzinfo is None  # naive UTC


def test_parse_rss_datetime_invalid_returns_now(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        dt = _parse_rss_datetime("not a date")
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    assert isinstance(dt, datetime)
    assert "パース失敗" in caplog.text


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


class _MockHeaders:
    def get(self, key, default=None):
        return default


class _MockResponse:
    def __init__(self, data: bytes, url: str = "https://dummy.rss"):
        self._data = data
        self._url = url
        self.headers = _MockHeaders()

    def read(self, n=-1):
        return self._data[:n] if n >= 0 else self._data

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_fetch_rss_parses_items(monkeypatch):
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(_SAMPLE_RSS),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert len(articles) == 2
    assert articles[0]["source"] == "test"
    assert articles[0]["title"] == "Toyota 7203 surge"
    assert "https://" not in articles[0]["content"]
    assert articles[0]["url"] == "https://news.example.com/article/1"
    assert len(articles[0]["id"]) == 32


def test_fetch_rss_skips_items_without_link(monkeypatch):
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(_SAMPLE_RSS),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert all(a["url"] for a in articles)


def test_fetch_rss_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        fetch_rss("file:///etc/passwd", source="test")


def test_fetch_rss_rejects_private_initial_url():
    """初回リクエスト前にホストがプライベートアドレスの場合は ValueError を送出すること。"""
    with pytest.raises(ValueError, match="プライベートアドレス"):
        fetch_rss("http://127.0.0.1/feed.rss", source="test")


def test_fetch_rss_skips_items_with_invalid_link_scheme(monkeypatch, caplog):
    """<link> が mailto: など非 http/https の item はスキップされること。"""
    import logging
    rss_with_bad_link = b"""<?xml version="1.0"?>
<rss><channel>
  <item><link>mailto:attacker@evil.com</link><title>Bad</title></item>
  <item><link>https://good.example.com/article</link><title>Good</title></item>
</channel></rss>"""
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(rss_with_bad_link),
    )
    with caplog.at_level(logging.WARNING):
        articles = fetch_rss("https://dummy.rss", source="test")
    assert len(articles) == 1
    assert articles[0]["url"] == "https://good.example.com/article"
    assert "不正なlinkスキーム" in caplog.text


def test_fetch_rss_no_channel_returns_empty(monkeypatch):
    no_channel = b"<?xml version='1.0'?><rss><title>X</title></rss>"
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(no_channel),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert articles == []


def test_fetch_rss_namespace_fallback(monkeypatch):
    """<channel> がない RSS でも .//item フォールバックで記事を取得できること。"""
    no_channel_with_items = b"""<?xml version="1.0"?>
<rss>
  <item>
    <link>https://example.com/fallback-article</link>
    <title>Fallback Article</title>
  </item>
</rss>"""
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(no_channel_with_items),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert len(articles) == 1
    assert articles[0]["url"] == "https://example.com/fallback-article"


def test_fetch_rss_invalid_content_length_is_ignored(monkeypatch):
    """Content-Length が非数値でも ValueError にならず記事を正常取得できること。"""
    class _BadCLHeaders:
        def get(self, key, default=None):
            if key == "Content-Length":
                return "not-a-number"
            return default

    class _BadCLResponse(_MockResponse):
        def __init__(self, data: bytes):
            super().__init__(data)
            self.headers = _BadCLHeaders()

    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _BadCLResponse(_SAMPLE_RSS),
    )
    articles = fetch_rss("https://dummy.rss", source="test")
    assert len(articles) == 2  # 不正な Content-Length は無視して通常解析


def test_fetch_rss_rejects_redirect_to_private_ip(monkeypatch, caplog):
    """リダイレクト後の最終 URL がプライベート IP の場合は空リストを返すこと。"""
    import logging

    class _PrivateIPResponse(_MockResponse):
        def geturl(self) -> str:
            return "http://127.0.0.1/rss"  # ループバックアドレス

    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _PrivateIPResponse(b""),
    )
    with caplog.at_level(logging.WARNING):
        articles = fetch_rss("https://dummy.rss", source="test")
    assert articles == []
    assert "プライベートアドレス" in caplog.text


def test_fetch_rss_invalid_xml_returns_empty(monkeypatch, caplog):
    import logging
    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _MockResponse(b"<not valid xml>>>"),
    )
    with caplog.at_level(logging.WARNING):
        articles = fetch_rss("https://dummy.rss", source="test")
    assert articles == []
    assert "XMLパース失敗" in caplog.text


def test_fetch_rss_gzip_decompressed_oversized_returns_empty(monkeypatch, caplog):
    """gzip 解凍後のサイズが MAX_RESPONSE_BYTES を超える場合は空リストを返すこと。"""
    import gzip as _gzip
    import logging
    from kabusys.data.news_collector import MAX_RESPONSE_BYTES

    # 解凍後が MAX_RESPONSE_BYTES+1 バイトになるデータを gzip 圧縮
    oversized = b"x" * (MAX_RESPONSE_BYTES + 1)
    compressed = _gzip.compress(oversized)

    class _GzipMockHeaders:
        def get(self, key, default=None):
            if key == "Content-Encoding":
                return "gzip"
            return default

    class _GzipMockResponse(_MockResponse):
        def __init__(self, data: bytes):
            super().__init__(data)
            self.headers = _GzipMockHeaders()

    monkeypatch.setattr(
        "kabusys.data.news_collector._urlopen",
        lambda req, timeout=30: _GzipMockResponse(compressed),
    )
    with caplog.at_level(logging.WARNING):
        articles = fetch_rss("https://dummy.rss", source="test")
    assert articles == []
    assert "gzip解凍後サイズ超過" in caplog.text


# ---------------------------------------------------------------------------
# save_raw_news テスト
# ---------------------------------------------------------------------------


def _make_article(idx: int = 1) -> dict:
    url = f"https://news.example.com/article/{idx}"
    return {
        "id": _make_article_id(url),
        "datetime": datetime(2024, 1, 15, 9, 0, 0),
        "source": "test",
        "title": f"Test article {idx}",
        "content": "body text",
        "url": url,
    }


def test_save_raw_news_basic(news_db):
    articles = [_make_article(1), _make_article(2)]
    saved = save_raw_news(news_db, articles)
    assert len(saved) == 2
    count = news_db.execute("SELECT COUNT(*) FROM raw_news").fetchone()[0]
    assert count == 2


def test_save_raw_news_returns_actual_inserted_count(news_db):
    """ON CONFLICT でスキップされた分はカウントしない。"""
    art = _make_article(1)
    save_raw_news(news_db, [art])
    saved2 = save_raw_news(news_db, [art])
    assert saved2 == []  # 重複はスキップ → 空リスト
    assert news_db.execute("SELECT COUNT(*) FROM raw_news").fetchone()[0] == 1


def test_save_raw_news_skips_missing_id(news_db):
    articles = [{"id": "", "datetime": datetime.now(), "source": "x",
                 "title": "t", "content": "", "url": "u"}]
    saved = save_raw_news(news_db, articles)
    assert saved == []


def test_save_raw_news_empty(news_db):
    assert save_raw_news(news_db, []) == []


# ---------------------------------------------------------------------------
# extract_stock_codes テスト
# ---------------------------------------------------------------------------


def test_extract_stock_codes_finds_known_codes():
    codes = extract_stock_codes("Toyota 7203 surge, Sony 6758 up", {"7203", "6758", "9999"})
    assert "7203" in codes
    assert "6758" in codes


def test_extract_stock_codes_ignores_unknown_codes():
    codes = extract_stock_codes("number 1234 here", {"7203"})
    assert codes == []


def test_extract_stock_codes_deduplicates():
    codes = extract_stock_codes("7203 and 7203 again", {"7203"})
    assert codes.count("7203") == 1


def test_extract_stock_codes_empty_text():
    assert extract_stock_codes("", {"7203"}) == []


def test_extract_stock_codes_no_known_codes():
    assert extract_stock_codes("7203 surge", set()) == []


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


def test_save_news_symbols_returns_actual_inserted_count(news_db):
    """ON CONFLICT でスキップされた分はカウントしない。"""
    art = _make_article(1)
    save_raw_news(news_db, [art])
    save_news_symbols(news_db, art["id"], ["7203"])
    saved2 = save_news_symbols(news_db, art["id"], ["7203"])
    assert saved2 == 0  # 重複はスキップ → 0 件


def test_save_news_symbols_empty(news_db):
    assert save_news_symbols(news_db, "x", []) == 0


# ---------------------------------------------------------------------------
# run_news_collection テスト
# ---------------------------------------------------------------------------


def test_run_news_collection_uses_default_sources(monkeypatch, news_db):
    captured_sources: list[str] = []

    def fake_fetch_rss(url, source, timeout=30):
        captured_sources.append(source)
        return [_make_article(1)]

    monkeypatch.setattr("kabusys.data.news_collector.fetch_rss", fake_fetch_rss)
    monkeypatch.setattr("kabusys.data.news_collector.save_raw_news", lambda conn, arts: [])

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
    def fail_fetch(url, source, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("kabusys.data.news_collector.fetch_rss", fail_fetch)
    results = run_news_collection(
        news_db,
        sources={"src1": "https://fail.rss", "src2": "https://also-fail.rss"},
    )
    assert results == {"src1": 0, "src2": 0}


def test_run_news_collection_extracts_symbols(monkeypatch, news_db):
    art = _make_article(1)
    art["title"] = "Toyota 7203 surge"
    art["content"] = "Sony 6758 also up"

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
