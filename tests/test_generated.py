
import gzip
import io
import time
from datetime import datetime, date, timedelta, timezone
from unittest import mock

import duckdb
import pytest

from kabusys import config
from kabusys.data import jquants_client as jq
from kabusys.data import news_collector as nc
from kabusys.data import schema
from kabusys.data import etl
from kabusys.data import quality


# ----------------------------
# config._parse_env_line
# ----------------------------
@pytest.mark.parametrize(
    "line,expected",
    [
        ("KEY=val", ("KEY", "val")),
        (" export FOO= 'a\\'b' #comment", ("FOO", "a'b")),
        ("KEY=val#notcomment", ("KEY", "val#notcomment")),  # '#' not preceded by space => kept
        ("# full comment", None),
        ("NOSEP", None),
        (" =no_key", None),
    ],
)
def test_parse_env_line_various(line, expected):
    res = config._parse_env_line(line)
    assert res == expected


# ----------------------------
# jquants_client: _to_float / _to_int
# ----------------------------
def test_to_float_and_to_int_behavior():
    assert jq._to_float(None) is None
    assert jq._to_float("") is None
    assert pytest.approx(jq._to_float("1.23"), 1e-6) == 1.23
    assert jq._to_float("abc") is None

    assert jq._to_int(None) is None
    assert jq._to_int("") is None
    assert jq._to_int("2") == 2
    assert jq._to_int(2) == 2
    assert jq._to_int("1.0") == 1
    assert jq._to_int("1.9") is None
    assert jq._to_int("notnum") is None


# ----------------------------
# jquants_client: _RateLimiter.wait
# ----------------------------
def test_rate_limiter_wait_uses_sleep(monkeypatch):
    rl = jq._RateLimiter(min_interval=2.0)
    # Simulate last called at t=100.0
    rl._last_called = 100.0

    # Monkeypatch time.monotonic to return 101.0 on first call (elapsed 1.0) and 102.0 on second call
    mono_calls = [101.0, 102.0]

    def fake_monotonic():
        return mono_calls.pop(0)

    slept = []

    def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr(jq.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(jq.time, "sleep", fake_sleep)

    rl.wait()
    # We expected to sleep for ~1.0s because min_interval=2.0 and elapsed=1.0
    assert slept and pytest.approx(slept[0], rel=1e-3) == 1.0
    # last_called updated
    assert rl._last_called == 102.0


# ----------------------------
# news_collector utilities
# ----------------------------
def test_normalize_url_and_make_id():
    url = "HTTPS://Example.COM/path?b=2&utm_source=x&a=1#frag"
    normalized = nc._normalize_url(url)
    assert "utm_source" not in normalized
    assert normalized.startswith("https://example.com/")
    # id is hex 32 chars
    aid = nc._make_article_id(url)
    assert isinstance(aid, str) and len(aid) == 32
    int(aid, 16)  # should be hex-decodable


def test_validate_url_scheme_rejects_non_http():
    with pytest.raises(ValueError):
        nc._validate_url_scheme("ftp://example.com/foo")


def test_is_private_host_ip_and_dns(monkeypatch):
    # direct IP private
    assert nc._is_private_host("127.0.0.1") is True
    # DNS resolving to private: mock getaddrinfo to return private address
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(2, 1, 6, "", ("10.0.0.1", 0))]

    monkeypatch.setattr(nc.socket, "getaddrinfo", fake_getaddrinfo)
    assert nc._is_private_host("somehost") is True

    # DNS resolution failure -> treated as non-private (safe)
    def raise_oserror(*args, **kwargs):
        raise OSError("dns fail")

    monkeypatch.setattr(nc.socket, "getaddrinfo", raise_oserror)
    assert nc._is_private_host("unresolvable") is False


def test_preprocess_text_removes_urls_and_normalizes_space():
    text = "This is  a test\nVisit https://example.com/foo?utm=1 now."
    out = nc.preprocess_text(text)
    assert "https://" not in out
    assert "\n" not in out
    assert "  " not in out
    assert out.startswith("This is a test")


def test_parse_rss_datetime_valid_and_invalid():
    s = "Mon, 01 Jan 2024 00:00:00 +0900"
    dt = nc._parse_rss_datetime(s)
    # dt should be naive UTC (tzinfo None) and represent UTC time
    assert isinstance(dt, datetime)
    assert dt.tzinfo is None
    # invalid yields current-ish time
    before = datetime.utcnow() - timedelta(seconds=5)
    dt2 = nc._parse_rss_datetime("not a date")
    assert isinstance(dt2, datetime)
    assert dt2.tzinfo is None
    assert dt2 >= before


# ----------------------------
# news_collector.fetch_rss (network interactions mocked)
# ----------------------------
class DummyResp:
    def __init__(self, raw_bytes: bytes, final_url="http://example.com/feed", headers=None):
        self._raw = raw_bytes
        self._final_url = final_url
        self.headers = headers or {}
    def geturl(self):
        return self._final_url
    def read(self, n=-1):
        # ignore n for simplicity
        return self._raw
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def make_rss_bytes(items: list[tuple[str, str, str]]):
    # items: list of (link, title, description)
    parts = ['<?xml version="1.0" encoding="utf-8"?><rss><channel>']
    for link, title, desc in items:
        parts.append(f"<item><link>{link}</link><title>{title}</title><description>{desc}</description></item>")
    parts.append("</channel></rss>")
    return "\n".join(parts).encode("utf-8")


def test_fetch_rss_simple(monkeypatch):
    raw = make_rss_bytes([("https://example.com/a", "T1", "D1")])
    resp = DummyResp(raw)
    monkeypatch.setattr(nc, "_urlopen", lambda req, timeout: resp)
    articles = nc.fetch_rss("https://example.com/feed", "example")
    assert len(articles) == 1
    art = articles[0]
    assert art["source"] == "example"
    assert art["title"] == "T1"
    assert art["content"] == "D1"
    assert art["url"] == "https://example.com/a"
    assert len(art["id"]) == 32


def test_fetch_rss_gzip_and_size_checks(monkeypatch):
    raw = make_rss_bytes([("https://example.com/a", "T", "D")])
    gz = gzip.compress(raw)
    headers = {"Content-Encoding": "gzip", "Content-Length": str(len(gz))}
    resp = DummyResp(gz, headers=headers)
    monkeypatch.setattr(nc, "_urlopen", lambda req, timeout: resp)
    arts = nc.fetch_rss("https://example.com/feed", "g")
    assert len(arts) == 1

    # Content-Length too big -> returns []
    big_headers = {"Content-Length": str(nc.MAX_RESPONSE_BYTES + 100)}
    big_resp = DummyResp(b"", headers=big_headers)
    monkeypatch.setattr(nc, "_urlopen", lambda req, timeout: big_resp)
    assert nc.fetch_rss("https://example.com/feed", "g") == []

    # raw read exceeding max -> returns []
    huge = b"a" * (nc.MAX_RESPONSE_BYTES + 2)
    huge_resp = DummyResp(huge, headers={})
    monkeypatch.setattr(nc, "_urlopen", lambda req, timeout: huge_resp)
    assert nc.fetch_rss("https://example.com/feed", "g") == []

    # invalid XML -> []
    bad_resp = DummyResp(b"<notxml", headers={})
    monkeypatch.setattr(nc, "_urlopen", lambda req, timeout: bad_resp)
    assert nc.fetch_rss("https://example.com/feed", "g") == []


# ----------------------------
# DB save / extract helpers
# ----------------------------
def test_save_raw_news_and_duplicates(monkeypatch):
    conn = schema.init_schema(":memory:")
    # prepare two articles
    now = datetime.utcnow()
    arts = [
        {"id": "id1", "datetime": now, "source": "s", "title": "t", "content": "c", "url": "https://a"},
        {"id": "id2", "datetime": now, "source": "s", "title": "t2", "content": "c2", "url": "https://b"},
    ]
    new_ids = nc.save_raw_news(conn, arts)
    assert set(new_ids) == {"id1", "id2"}
    # inserting same again yields no new ids
    new_ids2 = nc.save_raw_news(conn, arts)
    assert new_ids2 == []

    # Insert corresponding news_articles rows to satisfy FK for symbols tests
    for art in arts:
        conn.execute("INSERT INTO news_articles (id, datetime, source, title, content, url) VALUES (?, ?, ?, ?, ?, ?)",
                     [art["id"], art["datetime"], art["source"], art["title"], art["content"], art["url"]])

    # save_news_symbols
    saved = nc.save_news_symbols(conn, "id1", ["7203", "6758"])
    assert saved == 2
    # duplicate insertion returns 0 new
    saved2 = nc.save_news_symbols(conn, "id1", ["7203", "6758"])
    assert saved2 == 0


def test__save_news_symbols_bulk_and_extract_stock_codes():
    conn = schema.init_schema(":memory:")
    # insert minimal news_articles to satisfy FK
    conn.execute("INSERT INTO news_articles (id, datetime, source) VALUES (?, ?, ?)",
                 ["nid", datetime.utcnow(), "s"])
    pairs = [("nid", "7203"), ("nid", "7203"), ("nid", "6758")]
    saved = nc._save_news_symbols_bulk(conn, pairs)
    assert saved == 2  # unique pairs only
    # extract codes
    txt = "This mentions 7203 and 9999 and 7203 again"
    codes = nc.extract_stock_codes(txt, known_codes={"7203", "6758"})
    assert codes == ["7203"]


# ----------------------------
# ETL: run_prices_etl (with mocks)
# ----------------------------
def test_run_prices_etl_date_from_after_target(monkeypatch):
    conn = schema.init_schema(":memory:")
    # date_from > target_date behavior
    target = date(2022, 1, 1)
    res = etl.run_prices_etl(conn, target_date=target, date_from=target + timedelta(days=1))
    assert res == (0, 0)


def test_run_prices_etl_uses_min_date_when_no_last(monkeypatch):
    conn = schema.init_schema(":memory:")
    captured = {}

    def fake_fetch(id_token=None, date_from=None, date_to=None, code=None):
        captured["date_from"] = date_from
        captured["date_to"] = date_to
        return []

    monkeypatch.setattr(etl.jq, "fetch_daily_quotes", fake_fetch)
    monkeypatch.setattr(etl.jq, "save_daily_quotes", lambda conn, records: 0)

    target = date(2022, 1, 10)
    etl.run_prices_etl(conn, target_date=target)
    # date_from should be _MIN_DATA_DATE when DB empty
    assert captured["date_from"] == etl._MIN_DATA_DATE


# ----------------------------
# quality checks
# ----------------------------
def test_check_missing_data_and_spike_and_future_non_trading(monkeypatch):
    conn = schema.init_schema(":memory:")
    # insert two days for code '9999'
    d1 = date(2022, 1, 3)
    d2 = date(2022, 1, 4)
    # Insert a normal complete row for d1
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d1, "9999", 100.0, 110.0, 90.0, 100.0, 1000],
    )
    # Insert a row for d2 with missing open (should be captured by missing_data)
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d2, "9999", None, 150.0, 95.0, 150.0, 1000],
    )
    # Missing data check
    missing = quality.check_missing_data(conn, target_date=None)
    assert any(i.check_name == "missing_data" for i in missing)
    # Spike: create previous close small and current huge > threshold
    # Overwrite d1 close to small
    conn.execute("DELETE FROM raw_prices WHERE date = ? AND code = ?", [d1, "9999"])
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d1, "9999", 1.0, 1.0, 1.0, 1.0, 10],
    )
    conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d2, "9999", 100.0, 100.0, 100.0, 200.0, 10],
    )
    spikes = quality.check_spike(conn, target_date=None, threshold=0.5)
    assert any(i.check_name == "spike" for i in spikes)

    # future date detection
    future = date.today() + timedelta(days=10)
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 [future, "8888", 1.0, 1.0, 1.0, 1.0, 1])
    dt_issues = quality.check_date_consistency(conn, reference_date=date.today())
    assert any(i.check_name == "future_date" for i in dt_issues)

    # non_trading_day: add market_calendar row marking a date non-trading and raw_prices row
    some = date(2022, 2, 1)
    conn.execute("INSERT INTO market_calendar (date, is_trading_day, is_half_day, is_sq_day) VALUES (?, ?, ?, ?)",
                 [some, False, False, False])
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 [some, "7777", 10.0, 10.0, 10.0, 10.0, 1])
    dt_issues2 = quality.check_date_consistency(conn, reference_date=date.today())
    assert any(i.check_name == "non_trading_day" for i in dt_issues2)


# ----------------------------
# check_duplicates simulation by dropping PK and inserting duplicates
# ----------------------------
def test_check_duplicates_detects_groups():
    conn = schema.init_schema(":memory:")
    # Drop the table and recreate without a PK to simulate duplicates
    conn.execute("DROP TABLE raw_prices")
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE
        )
    """)
    d = date(2022, 3, 1)
    # insert duplicates
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)", [d, "1111", 1, 1, 1, 1])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)", [d, "1111", 1, 1, 1, 1])
    dups = quality.check_duplicates(conn, target_date=None)
    assert any(i.check_name == "duplicates" for i in dups)


if __name__ == "__main__":
    pytest.main([__file__])
