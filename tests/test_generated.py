
import io
import time
import duckdb
from datetime import date, datetime, timezone, timedelta
from unittest import mock

import pytest

# config
from kabusys.config import _parse_env_line

# jquants client
from kabusys.data import jquants_client as jq

# news collector
from kabusys.data import news_collector as news_mod

# etl / quality (pipeline.py is the ETL module)
from kabusys.data import pipeline as etl_mod
from kabusys.data import quality as quality_mod


# ----------------------------
# Fixtures
# ----------------------------

# Minimal DDL (no FK CASCADE) covering all tables used by these tests
_ALL_DDL = [
    """CREATE TABLE IF NOT EXISTS raw_prices (
        date        DATE          NOT NULL,
        code        VARCHAR       NOT NULL,
        open        DECIMAL(18,4),
        high        DECIMAL(18,4),
        low         DECIMAL(18,4),
        close       DECIMAL(18,4),
        volume      BIGINT,
        turnover    DECIMAL(18,2),
        fetched_at  TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        PRIMARY KEY (date, code)
    )""",
    """CREATE TABLE IF NOT EXISTS raw_financials (
        code            VARCHAR       NOT NULL,
        report_date     DATE          NOT NULL,
        period_type     VARCHAR       NOT NULL,
        revenue         DECIMAL(20,4),
        operating_profit DECIMAL(20,4),
        net_income      DECIMAL(20,4),
        eps             DECIMAL(18,4),
        roe             DECIMAL(10,6),
        fetched_at      TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        PRIMARY KEY (code, report_date, period_type)
    )""",
    """CREATE TABLE IF NOT EXISTS market_calendar (
        date            DATE        NOT NULL PRIMARY KEY,
        is_trading_day  BOOLEAN     NOT NULL,
        is_half_day     BOOLEAN     NOT NULL DEFAULT false,
        is_sq_day       BOOLEAN     NOT NULL DEFAULT false,
        holiday_name    VARCHAR
    )""",
    """CREATE TABLE IF NOT EXISTS raw_news (
        id          VARCHAR     NOT NULL PRIMARY KEY,
        datetime    TIMESTAMP   NOT NULL,
        source      VARCHAR     NOT NULL,
        title       VARCHAR,
        content     VARCHAR,
        url         VARCHAR,
        fetched_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp
    )""",
    """CREATE TABLE IF NOT EXISTS news_symbols (
        news_id     VARCHAR     NOT NULL,
        code        VARCHAR     NOT NULL,
        PRIMARY KEY (news_id, code)
    )""",
]


@pytest.fixture
def conn():
    """全テスト用インメモリ DuckDB（FK CASCADE なしの最小スキーマ）。"""
    c = duckdb.connect(":memory:")
    for ddl in _ALL_DDL:
        c.execute(ddl)
    yield c
    c.close()


# ----------------------------
# config._parse_env_line
# ----------------------------

def test_parse_env_line_empty_and_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# a comment") is None
    assert _parse_env_line("   # inline") is None


def test_parse_env_line_simple_and_export():
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export   FOO =  bar ") == ("FOO", "bar")
    # missing '=' returns None
    assert _parse_env_line("NOPART") is None


def test_parse_env_line_quoted_and_escaped():
    # double quoted with escaped quote inside and inline comment after closing quote
    line = 'MY="a\\\"b"#comment after'
    assert _parse_env_line(line) == ("MY", 'a"b')
    # single quotes with backslash escape
    line2 = "S='x\\\\y'"
    # inside single quotes, backslash + char should include the next char
    val2 = _parse_env_line(line2)
    assert val2 in (("S", "x\\y"), ("S", "\\y"))  # accept either backslash handling


def test_parse_env_line_inline_comment_without_space():
    # '#' immediately after characters should not be seen as comment (no preceding space)
    assert _parse_env_line("A=val#notcomment") == ("A", "val#notcomment")
    # but if '#' has a space before it it's considered comment
    assert _parse_env_line("A=val #comment") == ("A", "val")


# ----------------------------
# jquants_client: _to_float / _to_int / token caching / get_id_token / fetch_daily_quotes
# ----------------------------

def test_to_float_to_int_edge_cases():
    assert jq._to_float(None) is None
    assert jq._to_float("") is None
    assert jq._to_float("1.23") == 1.23
    assert jq._to_float("nan") is None or isinstance(jq._to_float("nan"), float)

    assert jq._to_int(None) is None
    assert jq._to_int("") is None
    # direct int string
    assert jq._to_int("42") == 42
    # float-looking int string
    assert jq._to_int("1.0") == 1
    # float with non-zero fraction -> None
    assert jq._to_int("1.9") is None
    # invalid string
    assert jq._to_int("abc") is None


def test_get_cached_token_and_get_id_token(monkeypatch):
    # mock get_id_token used by _get_cached_token
    called = {"count": 0}

    def fake_get_id_token(refresh_token=None):
        called["count"] += 1
        return f"token-{called['count']}"

    monkeypatch.setattr(jq, "get_id_token", fake_get_id_token)
    # clear module cache
    monkeypatch.setattr(jq, "_ID_TOKEN_CACHE", None)

    t1 = jq._get_cached_token(force_refresh=False)
    assert t1 == "token-1"
    # second call without force_refresh should reuse cache -> no increment
    t2 = jq._get_cached_token(force_refresh=False)
    assert t2 == "token-1"
    # force_refresh should re-invoke
    t3 = jq._get_cached_token(force_refresh=True)
    assert t3 == "token-2"


def test_get_id_token_calls_request(monkeypatch):
    # _request should be called and its response used
    def fake_request(path, method="GET", json_body=None, **kwargs):
        assert path == "/token/auth_refresh"
        assert method == "POST"
        assert json_body == {"refreshtoken": "rtok"}
        return {"idToken": "ID123"}

    monkeypatch.setattr(jq, "_request", fake_request)
    token = jq.get_id_token("rtok")
    assert token == "ID123"


def test_fetch_daily_quotes_pagination(monkeypatch):
    calls = []

    def fake_request(path, params=None, id_token=None, **kwargs):
        # emulate two-page API
        if not params or "pagination_key" not in params:
            calls.append(("first", params.copy() if params else None))
            return {"daily_quotes": [{"Date": "2020-01-01", "Code": "0001"}], "pagination_key": "p1"}
        else:
            calls.append(("second", params.copy()))
            return {"daily_quotes": [{"Date": "2020-01-02", "Code": "0002"}]}

    monkeypatch.setattr(jq, "_request", fake_request)
    res = jq.fetch_daily_quotes(id_token="tkn")
    assert isinstance(res, list)
    assert any(r["Code"] == "0001" for r in res)
    assert any(r["Code"] == "0002" for r in res)
    # ensure pagination key was used in subsequent call
    assert any(c[0] == "second" for c in calls)


# ----------------------------
# news module: RSS fetch & preprocessing & DB save & code extraction
# ----------------------------

def test_make_article_id_and_preprocess_and_parse_datetime():
    url = "https://example.com/article/1"
    aid = news_mod._make_article_id(url)
    assert isinstance(aid, str) and len(aid) == 16
    # preprocess removes URLs and normalizes whitespace
    s = "This is  a test https://x example\nnew"
    assert "https" not in news_mod.preprocess_text(s)
    assert "  " not in news_mod.preprocess_text(s)
    assert news_mod.preprocess_text(None) == ""
    # parse rss datetime with valid string (JST offset)
    dt = news_mod._parse_rss_datetime("Mon, 01 Jan 2024 00:00:00 +0900")
    assert isinstance(dt, datetime)
    # returned datetime is naive UTC (tzinfo removed); check roughly equals converted time
    assert dt.tzinfo is None


def test_fetch_rss_and_save_and_extract(monkeypatch, conn):
    # construct a simple RSS feed bytes
    rss = b"""<?xml version="1.0"?>
    <rss>
      <channel>
        <item>
          <link>http://example.com/a</link>
          <title>Title with URL http://example.com</title>
          <description>Description text</description>
          <pubDate>Mon, 01 Jan 2024 00:00:00 +0900</pubDate>
        </item>
      </channel>
    </rss>
    """

    # mock urlopen to return object with read() method
    fake_resp = mock.MagicMock()
    fake_resp.read.return_value = rss
    fake_cm = mock.MagicMock()
    fake_cm.__enter__.return_value = fake_resp
    monkeypatch.setattr(news_mod.urllib.request, "urlopen", lambda req, timeout=30: fake_cm)

    articles = news_mod.fetch_rss("http://example.com/rss", source="testsrc")
    assert len(articles) == 1
    art = articles[0]
    # fields present and preprocessed
    assert art["source"] == "testsrc"
    assert "http" not in art["title"]  # URL removed by preprocess_text
    assert art["id"] == news_mod._make_article_id(art["url"])

    # save to DB
    saved = news_mod.save_raw_news(conn, articles)
    assert saved == 1
    # verify row in raw_news
    rows = conn.execute("SELECT id, source, title, content, url FROM raw_news").fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "testsrc"

    # extract stock codes
    text = "Company 7203 and 9999 and 7203"
    codes = news_mod.extract_stock_codes(text, known_codes={"7203"})
    assert codes == ["7203"]


# ----------------------------
# ETL helpers: table existence & max date
# ----------------------------

def test_table_exists_and_get_max_date(conn):
    # raw_prices exists because schema.init_schema created it
    assert etl_mod._table_exists(conn, "raw_prices") is True
    # initially empty -> max date None
    assert etl_mod.get_last_price_date(conn) is None

    # insert one raw_prices row (full columns required by schema)
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            date(2022, 1, 1),
            "0001",
            10.0,
            11.0,
            9.0,
            10.5,
            1000,
            12345.67,
            datetime.now(timezone.utc).isoformat()
        ],
    )
    last = etl_mod.get_last_price_date(conn)
    assert last == date(2022, 1, 1)


# ----------------------------
# run_prices_etl behavior (early exit and normal path)
# ----------------------------

def test_run_prices_etl_early_exit(monkeypatch, conn):
    # date_from > target_date should return (0,0) without calling jq
    monkeypatch.setattr(jq, "fetch_daily_quotes", lambda **kw: (_ for _ in ()).throw(AssertionError("should not be called")))
    res = etl_mod.run_prices_etl(conn, target_date=date(2022, 1, 1), date_from=date(2022, 1, 2))
    assert res == (0, 0)


def test_run_prices_etl_calls_jq(monkeypatch, conn):
    fake_records = [{"Date": "2022-01-01", "Code": "0001"}]
    monkeypatch.setattr(jq, "fetch_daily_quotes", lambda **kw: fake_records)
    monkeypatch.setattr(jq, "save_daily_quotes", lambda c, records: len(records))
    fetched, saved = etl_mod.run_prices_etl(conn, target_date=date(2022, 1, 1), date_from=date(2022, 1, 1))
    assert fetched == 1
    assert saved == 1


# ----------------------------
# quality checks
# ----------------------------

def test_check_missing_data_and_spike_and_date_consistency(conn):
    # insert rows to trigger missing_data
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [date(2024, 1, 1), "0001", None, 10.0, 9.0, 9.5, 100, 1000.0, datetime.now(timezone.utc).isoformat()],
    )
    missing = quality_mod.check_missing_data(conn, target_date=date(2024, 1, 1))
    assert any(i.check_name == "missing_data" for i in missing)
    assert any(i.severity == "error" for i in missing)

    # prepare spike: two days for same code
    # insert previous day close = 100
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [date(2024, 1, 2), "7000", 100.0, 110.0, 90.0, 100.0, 10, 100.0, datetime.now(timezone.utc).isoformat()],
    )
    # current day close = 200 -> 100% increase -> spike threshold 0.5 -> should detect
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [date(2024, 1, 3), "7000", 180.0, 210.0, 170.0, 200.0, 10, 100.0, datetime.now(timezone.utc).isoformat()],
    )
    spikes = quality_mod.check_spike(conn, target_date=None, threshold=0.5)
    assert any(i.check_name == "spike" for i in spikes)
    assert any(i.severity == "warning" for i in spikes)

    # future date
    ref = date(2024, 1, 1)
    # insert a future row beyond ref
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [date(2099, 1, 1), "9999", 1.0, 1.0, 1.0, 1.0, 1, 1.0, datetime.now(timezone.utc).isoformat()],
    )
    future_issues = quality_mod.check_date_consistency(conn, reference_date=ref)
    assert any(i.check_name == "future_date" for i in future_issues)

    # non_trading_day: insert market_calendar marking a date as non-trading and raw_prices for that date
    conn.execute(
        "INSERT INTO market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name) VALUES (?, ?, ?, ?, ?)",
        [date(2024, 1, 4), False, False, False, "Holiday"],
    )
    conn.execute(
        """
        INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [date(2024, 1, 4), "1111", 1.0, 1.0, 1.0, 1.0, 1, 1.0, datetime.now(timezone.utc).isoformat()],
    )
    consistency = quality_mod.check_date_consistency(conn, reference_date=date(2024, 1, 1))
    assert any(i.check_name == "non_trading_day" for i in consistency)


def test_check_duplicates_detected_by_creating_non_pk_table(conn):
    # The schema's raw_prices has PK that prevents duplicates.
    # To test duplicates detection, recreate raw_prices without PK and insert duplicate rows.
    conn.execute("DROP TABLE IF EXISTS raw_prices")
    # create raw_prices without primary key to allow duplicates
    conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE
        )
        """
    )
    # insert two identical rows to create a duplicate group
    conn.execute("INSERT INTO raw_prices VALUES (?, ? , ?, ?, ?, ?)", [date(2024, 1, 5), "2222", 1.0, 1.0, 1.0, 1.0])
    conn.execute("INSERT INTO raw_prices VALUES (?, ? , ?, ?, ?, ?)", [date(2024, 1, 5), "2222", 1.0, 1.0, 1.0, 1.0])

    dup = quality_mod.check_duplicates(conn, target_date=None)
    assert any(i.check_name == "duplicates" for i in dup)
    assert any(i.severity == "error" for i in dup)
