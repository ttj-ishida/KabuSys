
import math
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from unittest import mock

import duckdb
import pytest

# 各モジュールをインポート
import kabusys.config as config
import kabusys.feature_engineering as fe
import kabusys.signal_generator as sg
import kabusys.feature_exploration as fexp
import kabusys.factor_research as fresearch
import kabusys.data.jquants_client as jq
import kabusys.data.news_collector as news
import kabusys.data.schema as schema
import kabusys.data.stats as stats
import kabusys.etl as etl


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------
@pytest.fixture
def conn():
    # インメモリ DuckDB
    c = duckdb.connect(":memory:")
    yield c
    c.close()


# ------------------------------------------------------------
# config._parse_env_line / Settings
# ------------------------------------------------------------
def test_parse_env_line_basic_cases():
    # コメント行 / 空行
    assert config._parse_env_line("") is None
    assert config._parse_env_line("# comment") is None

    # export prefix
    assert config._parse_env_line("export KEY=val") == ("KEY", "val")
    # spaces around
    assert config._parse_env_line("  KEY =  value  ") == ("KEY", "value")

    # no '='
    assert config._parse_env_line("NOTANASSIGN") is None

    # quoted with escapes
    line = r"MY='a\'b#c' # inline comment"
    # Expect value a'b#c (escape handled) and inline comment ignored due to quotes
    assert config._parse_env_line(line) == ("MY", "a'b#c")

    # unquoted with inline comment: '#' preceded by space is comment
    assert config._parse_env_line("X=12 #comment") == ("X", "12")
    # but if '#' is not preceded by space it's part of value
    assert config._parse_env_line("Y=ab#cd") == ("Y", "ab#cd")

    # empty key
    assert config._parse_env_line("=value") is None


def test_require_and_settings_properties(monkeypatch):
    # Ensure required keys cause ValueError when missing
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        _ = config._require("JQUANTS_REFRESH_TOKEN")

    # Provide environment values and test Settings
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "sbot")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "chid")
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DUCKDB_PATH", "~/db.duckdb")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/monitor.db")

    s = config.Settings()
    assert s.jquants_refresh_token == "tok"
    assert s.kabu_api_password == "pw"
    assert s.slack_bot_token == "sbot"
    assert s.slack_channel_id == "chid"
    # env lowercased but validated against _VALID_ENVS
    assert s.env == "live"
    assert s.is_live is True and s.is_dev is False
    # LOG_LEVEL uppercased
    assert s.log_level == "DEBUG"
    # path expansion returns Path-like object
    assert str(s.duckdb_path).endswith("db.duckdb")
    assert str(s.sqlite_path).endswith("monitor.db")

    # invalid env value
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    # invalid log level
    monkeypatch.setenv("LOG_LEVEL", "NOTALEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level


# ------------------------------------------------------------
# feature_engineering._apply_universe_filter / build_features
# ------------------------------------------------------------
def test_apply_universe_filter_edge_cases():
    records = [
        {"code": "A", "avg_turnover": 6e8},  # price map missing -> excluded
        {"code": "B", "avg_turnover": 6e8},
        {"code": "C", "avg_turnover": 1e9},
        {"code": "D", "avg_turnover": None},
        {"code": "E", "avg_turnover": float("nan")},
    ]
    price_map = {"B": 100.0, "C": 300.0, "D": 400.0, "E": 1000.0}
    # B price too low (<300), C ok, D avg_turnover None excluded, E avg_turnover nan excluded
    filtered = fe._apply_universe_filter(records, price_map)
    codes = [r["code"] for r in filtered]
    assert codes == ["C"]


def test_build_features_basic(monkeypatch, conn):
    # Prepare minimal tables used by build_features
    conn.execute(
        """
        CREATE TABLE prices_daily (
            date DATE, code VARCHAR, close DOUBLE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE features (
            date DATE, code VARCHAR, momentum_20 DOUBLE, momentum_60 DOUBLE,
            volatility_20 DOUBLE, volume_ratio DOUBLE, per DOUBLE, ma200_dev DOUBLE, created_at TIMESTAMP
        )
        """
    )
    target = date(2024, 1, 10)

    # Prepare prices: for code '1001' and '1002' latest price before or on target
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [target, "1001", 500.0])
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [target - timedelta(days=1), "1002", 400.0])

    # Mock calc_* to return raw factor dicts
    mom_list = [{"code": "1001", "mom_1m": 1.0, "mom_3m": 2.0, "ma200_dev": 0.1},
                {"code": "1002", "mom_1m": None, "mom_3m": 0.5, "ma200_dev": None}]
    vol_list = [{"code": "1001", "atr_pct": 0.02, "volume_ratio": 1.2},
                {"code": "1002", "atr_pct": 0.5, "volume_ratio": 0.9}]
    val_list = [{"code": "1001", "per": 10.0, "avg_turnover": 6e8},
                {"code": "1002", "per": None, "avg_turnover": 6e8}]

    monkeypatch.setattr(fe, "calc_momentum", lambda conn_, td: mom_list)
    monkeypatch.setattr(fe, "calc_volatility", lambda conn_, td: vol_list)
    monkeypatch.setattr(fe, "calc_value", lambda conn_, td: val_list)

    # Mock zscore_normalize to slightly alter values (simulate normalization), include an outlier to be clipped
    def fake_zscore(records, cols):
        out = []
        for r in records:
            nr = r.copy()
            # set norm cols to values that cause clipping when >3
            for c in cols:
                nr[c] = 10.0 if nr.get(c) is None else nr.get(c) * 10.0
            out.append(nr)
        return out

    monkeypatch.setattr(fe, "zscore_normalize", fake_zscore)

    count = fe.build_features(conn, target)
    assert count == 2  # two merged codes pass through avg_turnover filter

    # verify rows inserted into features
    rows = conn.execute("SELECT code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev FROM features WHERE date = ?", [target]).fetchall()
    assert len(rows) == 2
    # momentum_20 values were clipped to +/-3 by build_features; fake_zscore gave large numbers -> clipped to 3 or -3
    for code, m20, m60, vol20, vr, per, ma200 in rows:
        if m20 is not None:
            assert abs(m20) <= 3.0


# ------------------------------------------------------------
# signal_generator: utilities and generate_signals
# ------------------------------------------------------------
def test_sigmoid_and_avg_scores_and_value_score():
    # sigmoid handles None
    assert sg._sigmoid(None) is None
    # large positive -> near 1, large negative -> near 0
    assert sg._sigmoid(100.0) > 0.999
    assert sg._sigmoid(-100.0) < 0.001

    # avg scores ignores None and non-finite
    assert sg._avg_scores([None, 1.0, float("nan"), 3.0]) == pytest.approx(2.0)

    # compute_value_score: valid per
    assert sg._compute_value_score({"per": 20}) == pytest.approx(1.0 / (1.0 + 20.0 / 20.0))
    # non-positive per returns None
    assert sg._compute_value_score({"per": 0}) is None
    assert sg._compute_value_score({"per": None}) is None


def test_is_bear_regime_samples_and_threshold():
    # insufficient samples -> False
    ai_map = {"A": {"regime_score": -1.0}, "B": {"regime_score": None}}
    assert sg._is_bear_regime(ai_map) is False

    # sufficient samples and negative average -> True
    ai_map = {"A": {"regime_score": -0.5}, "B": {"regime_score": -0.6}, "C": {"regime_score": -1.0}}
    assert sg._is_bear_regime(ai_map) is True

    # positive average -> False
    ai_map = {"A": {"regime_score": 0.1}, "B": {"regime_score": 0.2}, "C": {"regime_score": -0.1}}
    assert sg._is_bear_regime(ai_map) is False


def test_generate_signals_buy_and_sell(monkeypatch, conn):
    # prepare tables
    conn.execute("""CREATE TABLE features (
        date DATE, code VARCHAR, momentum_20 DOUBLE, momentum_60 DOUBLE,
        volatility_20 DOUBLE, volume_ratio DOUBLE, per DOUBLE, ma200_dev DOUBLE
    )""")
    conn.execute("""CREATE TABLE ai_scores (
        date DATE, code VARCHAR, sentiment_score DOUBLE, regime_score DOUBLE, ai_score DOUBLE
    )""")
    conn.execute("""CREATE TABLE positions (
        date DATE, code VARCHAR, position_size BIGINT, avg_price DOUBLE
    )""")
    conn.execute("""CREATE TABLE prices_daily (date DATE, code VARCHAR, close DOUBLE)""")
    conn.execute("""CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score DOUBLE, signal_rank INTEGER)""")

    target = date(2024, 2, 1)

    # feature for two codes: one good (high momentum), one mediocre
    conn.executemany("INSERT INTO features VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        (target, "C1", 2.0, 1.0, -1.0, 1.0, 10.0, 0.5),
        (target, "C2", 0.0, 0.0, 0.0, 0.5, 30.0, -1.0),
    ])
    # ai_scores: neutral for both, regime scores positive to avoid bear suppression
    conn.executemany("INSERT INTO ai_scores VALUES (?, ?, ?, ?, ?)", [
        (target, "C1", 0.0, 0.1, 0.0),
        (target, "C2", 0.0, 0.2, 0.0),
        # include extra ai score to ensure _is_bear_regime sees >= _BEAR_MIN_SAMPLES
        (target, "X", 0.0, 0.3, 0.0),
    ])
    # positions: add a position that will trigger stop_loss for C2
    conn.executemany("INSERT INTO positions VALUES (?, ?, ?, ?)", [
        (target, "C2", 10, 200.0),
    ])
    # prices: close for C2 triggers stop loss (close/avg_price -1 < -0.08)
    conn.executemany("INSERT INTO prices_daily VALUES (?, ?, ?)", [
        (target, "C1", 300.0),
        (target, "C2", 180.0),
    ])

    total = sg.generate_signals(conn, target, threshold=0.4)
    # Expect: C1 BUY (score >= threshold), C2 SELL (stop_loss)
    assert total == 2

    rows = conn.execute("SELECT code, side FROM signals WHERE date = ?", [target]).fetchall()
    assert set(rows) == {("C1", "buy"), ("C2", "sell")}


# ------------------------------------------------------------
# feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary
# ------------------------------------------------------------
def test_calc_forward_returns_and_horizon_validation(conn):
    conn.execute("CREATE TABLE prices_daily (date DATE, code VARCHAR, close DOUBLE)")
    # create sequential dates for code 'Z' with increasing close
    base = date(2024, 1, 1)
    dates = [base + timedelta(days=i) for i in range(10)]
    for i, d in enumerate(dates):
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [d, "Z", 100.0 + i])
    # valid default horizons
    res = fexp.calc_forward_returns(conn, base + timedelta(days=2))
    # result should contain code Z
    assert any(r["code"] == "Z" for r in res)
    # invalid horizons raise
    with pytest.raises(ValueError):
        fexp.calc_forward_returns(conn, base, horizons=[0, -1, 300])


def test_rank_and_calc_ic_and_factor_summary():
    vals = [1.0, 2.0, 2.0, 4.0]  # ties in middle
    ranks = fexp.rank(vals)
    # expected ranks: 1, (2+3)/2=2.5, 2.5, 4
    assert ranks == pytest.approx([1.0, 2.5, 2.5, 4.0])

    # prepare factor and forward records for Spearman: simple monotonic relation -> rho=1.0
    factor_records = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}, {"code": "C", "f": 3.0}]
    forward_records = [{"code": "A", "r": 10.0}, {"code": "B", "r": 20.0}, {"code": "C", "r": 30.0}]
    rho = fexp.calc_ic(factor_records, forward_records, "f", "r")
    assert rho == pytest.approx(1.0)

    # insufficient pairs -> None
    rho = fexp.calc_ic([{"code": "A", "f": 1.0}], forward_records, "f", "r")
    assert rho is None

    # factor_summary
    records = [{"c": 1.0}, {"c": 2.0}, {"c": None}, {"c": 4.0}]
    summary = fexp.factor_summary(records, ["c", "x"])
    assert summary["c"]["count"] == 3
    assert summary["x"]["count"] == 0
    assert summary["c"]["min"] == 1.0
    assert summary["c"]["max"] == 4.0


# ------------------------------------------------------------
# factor_research: small integration for calc_value / calc_momentum / calc_volatility
# ------------------------------------------------------------
def test_calc_value_and_momentum_and_volatility_basic(conn):
    # create prices_daily and raw_financials with minimal columns used
    conn.execute("""
    CREATE TABLE prices_daily (
        date DATE, code VARCHAR, close DOUBLE, high DOUBLE, low DOUBLE, volume BIGINT, turnover DOUBLE
    )""")
    conn.execute("""
    CREATE TABLE raw_financials (
        code VARCHAR, report_date DATE, eps DOUBLE, roe DOUBLE, fetched_at TIMESTAMP, period_type VARCHAR
    )""")
    # insert price on target
    target = date(2024, 3, 1)
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?, ?, ?, ?, ?)", [target, "AA", 200.0, 205.0, 195.0, 1000, 1e9])
    # insert financials <= target
    conn.execute("INSERT INTO raw_financials VALUES (?, ?, ?, ?, ?, ?)", ["AA", target - timedelta(days=10), 10.0, 0.1, datetime.now(), "Q"])
    # calc_value should return per = 200/10 = 20
    v = fresearch.calc_value(conn, target)
    assert any(r["code"] == "AA" and pytest.approx(r["per"], rel=1e-6) == 20.0 for r in v)

    # For momentum and volatility we need multiple dates to compute LAG and windows.
    # Insert 200+ days for moving average to produce ma200_dev (but we will simplify: insert enough rows)
    base = target - timedelta(days=400)
    # create many rows for code BB
    for i in range(220):
        d = base + timedelta(days=i)
        close = 100.0 + i * 0.1
        high = close + 1.0
        low = close - 1.0
        vol = 1000 + i
        turnover = vol * close
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?, ?, ?, ?, ?)", [d, "BB", close, high, low, vol, turnover])
    # call momentum/volatility for BB
    mom = fresearch.calc_momentum(conn, target)
    # BB should be present
    assert any(r["code"] == "BB" for r in mom)
    vol = fresearch.calc_volatility(conn, target)
    assert any(r["code"] == "BB" for r in vol)


# ------------------------------------------------------------
# jquants_client: _to_float / _to_int
# ------------------------------------------------------------
def test_to_float_and_to_int_edge_cases():
    assert jq._to_float(None) is None
    assert jq._to_float("") is None
    assert jq._to_float("12.3") == pytest.approx(12.3)
    assert jq._to_float("bad") is None

    assert jq._to_int(None) is None
    assert jq._to_int("") is None
    assert jq._to_int("5") == 5
    assert jq._to_int(5.0) == 5
    # non-integer float string -> None
    assert jq._to_int("1.9") is None
    # invalid -> None
    assert jq._to_int("abc") is None


# ------------------------------------------------------------
# news_collector: url normalization, id, preprocess_text, extract codes
# ------------------------------------------------------------
def test_news_collector_utilities():
    url = "https://Example.COM/path?utm_source=x&b=2&a=1#frag"
    norm = news._normalize_url(url)
    # scheme and host lowered, utm removed, query params sorted (a,b)
    assert norm.startswith("https://example.com/path?")
    assert "utm_" not in norm and "#" not in norm

    # id generation stable
    id1 = news._make_article_id(url)
    id2 = news._make_article_id(url)
    assert id1 == id2 and len(id1) == 32

    # preprocess_text
    txt = "This is a test https://example.com/page   \n next"
    assert news.preprocess_text(txt) == "This is a test next"
    assert news.preprocess_text(None) == ""

    # extract_stock_codes
    text = "News about 7203 and 6758 and 7203 again"
    codes = news.extract_stock_codes(text, {"7203", "6758", "9999"})
    assert set(codes) == {"7203", "6758"}


# ------------------------------------------------------------
# schema.init_schema minimal check
# ------------------------------------------------------------
def test_init_schema_creates_tables(tmp_path):
    db = tmp_path / "test.db"
    conn = schema.init_schema(str(db))
    # basic table existence check: prices_daily should exist
    row = conn.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'prices_daily'").fetchone()
    assert row is not None
    conn.close()


# ------------------------------------------------------------
# stats.zscore_normalize
# ------------------------------------------------------------
def test_zscore_normalize_basic():
    recs = [
        {"code": "A", "x": 1.0, "y": None},
        {"code": "B", "x": 2.0, "y": 5.0},
        {"code": "C", "x": 3.0, "y": 7.0},
    ]
    out = stats.zscore_normalize(recs, ["x", "y"])
    # x: mean=2.0 std=sqrt(2/3)=~0.816496... => (1-2)/std ~= -1.2247
    assert out[0]["x"] == pytest.approx((1.0 - 2.0) / math.sqrt(((1.0 - 2.0) ** 2 + (2.0 - 2.0) ** 2 + (3.0 - 2.0) ** 2) / 3))
    # y: only 2 valid values -> normalization applied across those two
    assert out[1]["y"] is not None


# ------------------------------------------------------------
# etl.ETLResult behaviour and helpers
# ------------------------------------------------------------
def test_etl_result_and_table_helpers(conn):
    target = date(2024, 1, 1)
    er = etl.ETLResult(target_date=target)
    assert not er.has_errors
    # quality_issues uses objects; simulate with simple NamedTuple-like
    class Q:
        def __init__(self, check_name, severity, message):
            self.check_name = check_name
            self.severity = severity
            self.message = message

    er.quality_issues.append(Q("c", "error", "m"))
    assert er.has_quality_errors

    d = er.to_dict()
    assert "quality_issues" in d and isinstance(d["quality_issues"], list)

    # table helpers: when table not exists should return None
    assert etl._table_exists(conn, "nonexistent_table") is False
    assert etl._get_max_date(conn, "nonexistent_table", "date") is None

    # test _adjust_to_trading_day: create market_calendar with a trading day earlier than target
    conn.execute("CREATE TABLE market_calendar (date DATE, is_trading_day BOOLEAN)")
    conn.execute("INSERT INTO market_calendar VALUES (?, ?)", [target - timedelta(days=3), True])
    adjusted = etl._adjust_to_trading_day(conn, target)
    assert adjusted <= target
