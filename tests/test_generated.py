
import os
import hashlib
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import mock

import duckdb
import pytest

# config
from kabusys.config import _parse_env_line, _require, Settings

# research (feature exploration)
from kabusys.research import (
    calc_forward_returns,
    calc_ic,
    _rank,
    factor_summary,
)

# features (zscore)
from kabusys.data.features import zscore_normalize

# jquants client utils
from kabusys.data.jquants_client import _to_float, _to_int, get_id_token

# schema init
from kabusys.data.schema import init_schema

# news collector
from kabusys.data import news_collector as nc

# etl
from kabusys.data.etl import ETLResult

# -------------------------
# config tests
# -------------------------


def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("  # comment ") is None
    # no separator
    assert _parse_env_line("NOSEP") is None
    # simple unquoted with inline comment recognized only if preceded by space
    assert _parse_env_line("BAR=1 #ignored") == ("BAR", "1")
    # export prefix
    assert _parse_env_line("export X=val") == ("X", "val")
    # quoted with escaped quote and '#' inside quotes should be preserved
    # FOO='a\'b#c'  -> value should be: a'b#c
    line = "FOO='a\\'b#c'   #comment"
    assert _parse_env_line(line) == ("FOO", "a'b#c")
    # double quoted with escaped quote
    line2 = 'Q="x\\\"y"'
    assert _parse_env_line(line2) == ("Q", 'x"y')


def test_require_raises_and_ok(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_VAR", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_MISSING_VAR")
    monkeypatch.setenv("SOME_MISSING_VAR", "value")
    assert _require("SOME_MISSING_VAR") == "value"


def test_settings_env_and_log_level(monkeypatch):
    s = Settings()
    # default env is development
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert s.env == "development"
    # valid values
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.env == "live"
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.env == "paper_trading"
    # invalid value
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    # log level default INFO
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert s.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "BAD")
    with pytest.raises(ValueError):
        _ = s.log_level


# -------------------------
# research tests (_rank, calc_ic, calc_forward_returns, factor_summary)
# -------------------------


def test_rank_with_ties():
    vals = [10.0, 20.0, 20.0, 30.0]
    ranks = _rank(vals)
    # expected ranks: 1.0, 2.5, 2.5, 4.0
    assert pytest.approx(ranks[0]) == 1.0
    assert pytest.approx(ranks[1]) == 2.5
    assert pytest.approx(ranks[2]) == 2.5
    assert pytest.approx(ranks[3]) == 4.0


def test_calc_ic_insufficient_and_perfect_correlation():
    # insufficient records (<3)
    factor = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}]
    fwd = [{"code": "A", "r": 0.1}, {"code": "B", "r": 0.2}]
    assert calc_ic(factor, fwd, "f", "r") is None

    # perfect monotonic correlation -> Spearman rho == 1.0
    factor = [
        {"code": "C", "f": 1.0},
        {"code": "D", "f": 2.0},
        {"code": "E", "f": 3.0},
    ]
    fwd = [
        {"code": "C", "r": 10.0},
        {"code": "D", "r": 20.0},
        {"code": "E", "r": 30.0},
    ]
    rho = calc_ic(factor, fwd, "f", "r")
    assert pytest.approx(rho) == 1.0

    # negative monotonic
    factor = [
        {"code": "X", "f": 1.0},
        {"code": "Y", "f": 2.0},
        {"code": "Z", "f": 3.0},
    ]
    fwd = [
        {"code": "X", "r": 30.0},
        {"code": "Y", "r": 20.0},
        {"code": "Z", "r": 10.0},
    ]
    rho = calc_ic(factor, fwd, "f", "r")
    assert pytest.approx(rho) == -1.0


def test_calc_forward_returns_basic():
    conn = duckdb.connect(":memory:")
    # create minimal prices_daily table used by calc_forward_returns
    conn.execute(
        """
        CREATE TABLE prices_daily (
            date DATE,
            code VARCHAR,
            close DOUBLE
        )
        """
    )
    # target_date and future dates
    t = date(2020, 1, 1)
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [t, "0001", 100.0])
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [date(2020, 1, 2), "0001", 110.0])
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [date(2020, 1, 6), "0001", 120.0])
    # another code missing future -> returns None
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [t, "0002", 50.0])

    res = calc_forward_returns(conn, t, horizons=[1, 5])
    # should have two codes, ordered by code
    codes = [r["code"] for r in res]
    assert "0001" in codes and "0002" in codes
    r1 = next(r for r in res if r["code"] == "0001")
    # fwd_1d = (110 - 100) / 100 = 0.1
    assert pytest.approx(r1["fwd_1d"]) == 0.1
    # fwd_5d = (120 - 100) / 100 = 0.2
    assert pytest.approx(r1["fwd_5d"]) == 0.2
    r2 = next(r for r in res if r["code"] == "0002")
    assert r2["fwd_1d"] is None and r2["fwd_5d"] is None


def test_factor_summary_and_median_even_odd():
    records = [
        {"a": 1.0, "b": None},
        {"a": 2.0, "b": 3.0},
        {"a": 3.0, "b": 6.0},
        {"a": None, "b": 9.0},
    ]
    summary = factor_summary(records, ["a", "b", "c"])
    # 'a' has values [1,2,3] median=2
    assert summary["a"]["count"] == 3
    assert pytest.approx(summary["a"]["mean"]) == 2.0
    assert summary["a"]["median"] == 2.0
    # 'b' has values [3,6,9] median=6
    assert summary["b"]["count"] == 3
    assert pytest.approx(summary["b"]["mean"]) == 6.0
    assert summary["b"]["median"] == 6.0
    # 'c' absent -> all None
    assert summary["c"]["count"] == 0
    assert summary["c"]["mean"] is None


# -------------------------
# features: zscore_normalize
# -------------------------


def test_zscore_normalize_basic_and_none_and_single():
    records = [
        {"code": "A", "val": 1.0},
        {"code": "B", "val": 3.0},
        {"code": "C", "val": None},
    ]
    out = zscore_normalize(records, ["val"])
    # mean = 2, std = 1 -> zscores [-1, +1], None preserved
    vals = {r["code"]: r["val"] for r in out}
    assert pytest.approx(vals["A"], rel=1e-6) == -1.0
    assert pytest.approx(vals["B"], rel=1e-6) == 1.0
    assert vals["C"] is None

    # single record -> no normalization performed (len <=1)
    single = [{"code": "A", "val": 10.0}]
    out2 = zscore_normalize(single, ["val"])
    assert out2[0]["val"] == 10.0


# -------------------------
# jquants_client utils tests
# -------------------------


def test_to_float_and_to_int_edge_cases():
    assert _to_float(None) is None
    assert _to_float("") is None
    assert _to_float("1.23") == pytest.approx(1.23)
    assert _to_float("abc") is None

    assert _to_int(None) is None
    assert _to_int("") is None
    assert _to_int("1") == 1
    assert _to_int("1.0") == 1
    assert _to_int("1.9") is None
    assert _to_int("abc") is None


def test_get_id_token_uses_request_and_env(monkeypatch):
    # patch the internal _request used by get_id_token to return an idToken
    import kabusys.data.jquants_client as jc

    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "dummy_refresh")
    with mock.patch.object(jc, "_request", return_value={"idToken": "ID123"}) as m:
        token = get_id_token()
        assert token == "ID123"
        m.assert_called_once()
    # if no refresh token in env, get_id_token should raise ValueError
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        get_id_token(None)


# -------------------------
# schema init test
# -------------------------


def test_init_schema_creates_tables():
    conn = init_schema(":memory:")
    # check that a few expected tables exist
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE lower(table_name) = lower('raw_prices')"
    ).fetchone()
    assert row is not None
    # check another table
    row2 = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE lower(table_name) = lower('prices_daily')"
    ).fetchone()
    assert row2 is not None
    conn.close()


# -------------------------
# news_collector utils and save_raw_news
# -------------------------


def test_normalize_url_and_make_article_id_and_preprocess_text():
    url = "HTTPS://Example.COM/path?utm_source=aa&b=2#frag"
    norm = nc._normalize_url(url)
    assert "utm_source" not in norm
    assert "#" not in norm
    assert norm.startswith("https://")
    # article id is 32-hex prefix
    aid = nc._make_article_id(url)
    assert isinstance(aid, str) and len(aid) == 32
    # preprocess text removes urls and collapses whitespace
    txt = "Visit https://x.com  \n\n and  enjoy"
    assert nc.preprocess_text(txt) == "Visit and enjoy"
    # None -> empty
    assert nc.preprocess_text(None) == ""


def test_parse_rss_datetime_and_extract_stock_codes():
    # RFC2822 with timezone +0900 -> should convert to UTC naive
    s = "Mon, 01 Jan 2024 00:00:00 +0900"
    dt = nc._parse_rss_datetime(s)
    # dt should be naive and represent UTC time (i.e., 2023-12-31 15:00:00 UTC)
    assert dt.tzinfo is None
    # extract stock codes from text, only known codes allowed and duplicates removed
    text = "This mentions 7203 and 6758 and 7203 again"
    codes = nc.extract_stock_codes(text, {"7203", "6758", "9999"})
    assert set(codes) == {"7203", "6758"}
    # no known codes -> empty
    assert nc.extract_stock_codes("No codes here 1234", {"0000"}) == []


def test_save_raw_news_idempotent(tmp_path):
    conn = init_schema(":memory:")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    art = {
        "id": "id1",
        "datetime": now,
        "source": "test",
        "title": "t",
        "content": "c",
        "url": "https://example.com/a",
    }
    # first save -> returns ['id1']
    from kabusys.data.news_collector import save_raw_news

    inserted = save_raw_news(conn, [art])
    assert inserted == ["id1"]
    # second save same article -> returns []
    inserted2 = save_raw_news(conn, [art])
    assert inserted2 == []
    conn.close()


# -------------------------
# ETLResult dataclass
# -------------------------


def test_etlresult_to_dict_and_flags():
    # create dummy quality issue like object
    qi = SimpleNamespace(check_name="chk", severity="error", message="bad")
    r = ETLResult(target_date=date(2020, 1, 1), quality_issues=[qi], errors=["e"])
    d = r.to_dict()
    assert d["target_date"] == date(2020, 1, 1)
    assert r.has_errors is True
    assert r.has_quality_errors is True
    assert isinstance(d["quality_issues"], list)
    assert d["quality_issues"][0]["check_name"] == "chk"
