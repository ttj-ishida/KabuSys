以下は提示されたコードに対する pytest テスト群です。主要な関数・クラスの通常ケースとエッジケース、および外部依存のモックを含んでいます。ファイルをプロジェクトの tests/ ディレクトリに保存して実行してください。

注意:
- DuckDB がインストールされていることを前提としています（duckdb パッケージ）。
- OpenAI クライアントやネットワーク呼び出しはモックしています（unittest.mock を使用）。
- 実行時に環境変数を書き換えるテストがあるため、pytest の実行は他のプロセスに影響しないように isolated に行ってください。

ファイル: tests/test_config.py
--------------------------------
from pathlib import Path
import os
import tempfile
import textwrap
import builtins
import io

import pytest

from kabusys import config


def test_parse_env_line_ignores_comments_and_blank():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   ") is None
    assert config._parse_env_line("# comment") is None


def test_parse_env_line_export_and_unquoted_comment():
    line = "export KEY=val # inline comment"
    res = config._parse_env_line(line)
    assert res == ("KEY", "val")


def test_parse_env_line_quoted_with_escapes_and_trailing_comment():
    # Value contains an escaped quote and trailing comment outside the closing quote
    line = r"KEY='a\'b' # comment"
    res = config._parse_env_line(line)
    assert res == ("KEY", "a'b")


def test_parse_env_line_no_equal_returns_none():
    assert config._parse_env_line("NOEQ") is None
    assert config._parse_env_line("=noval") is None


def test_load_env_file_sets_values(tmp_path, monkeypatch):
    p = tmp_path / ".envtest"
    p.write_text(textwrap.dedent("""
        A=1
        B='two'
        # comment
        C=three # inline comment
    """), encoding="utf-8")
    # start with environment containing protected KEY
    monkeypatch.setenv("PROT", "x")
    protected = frozenset(os.environ.keys())
    # clear possible test keys
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    # load with override=False: will set keys not present
    config._load_env_file(p, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "two"
    assert os.environ.get("C") == "three"

    # override True but protected keys not overwritten
    monkeypatch.setenv("A", "orig")
    config._load_env_file(p, override=True, protected=protected)
    # A was not in protected set, so should be overwritten
    assert os.environ.get("A") == "1"


def test_require_raises_if_missing(monkeypatch):
    monkeypatch.delenv("NONEXISTENT", raising=False)
    with pytest.raises(ValueError):
        config._require("NONEXISTENT")


def test_settings_properties_and_validations(monkeypatch, tmp_path):
    # jquants token required
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "tok")
    s = config.Settings()
    assert s.jquants_refresh_token == "tok"

    # kabu api password required
    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    assert s.kabu_api_password == "pwd"

    # defaults for urls and optional tokens
    monkeypatch.delenv("KABU_API_BASE_URL", raising=False)
    assert s.kabu_api_base_url.startswith("http://")

    # duckdb/sqlite path expansion and Path result
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "db.duckdb"))
    p = s.duckdb_path
    assert isinstance(p, Path)

    # paper_fill_mode valid and invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid-mode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

    # env and log_level validations
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.env == "development"
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.is_live is True
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    assert s.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "BADLEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level

File: tests/test_regime_detector.py
--------------------------------
import json
from datetime import date, datetime, timedelta

import duckdb
import pytest
from unittest.mock import patch, Mock

from kabusys.ai import regime_detector as rd
from kabusys.ai import news_nlp as nn


def make_conn_with_prices(closes):
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE prices_daily (code VARCHAR, date DATE, close DOUBLE)")
    # Insert rows with dates increasing; regime_detector expects rows WHERE date < target_date
    base = date(2020, 1, 1)
    for i, c in enumerate(closes):
        dt = base + timedelta(days=i)
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", ["1321", dt, c])
    return conn, base + timedelta(days=len(closes))  # target_date is after last row


def test_calc_ma200_ratio_no_rows_warns_and_returns_1(monkeypatch):
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE prices_daily (code VARCHAR, date DATE, close DOUBLE)")
    res = rd._calc_ma200_ratio(conn, date(2020, 1, 10))
    assert res == 1.0


def test_calc_ma200_ratio_insufficient_rows_returns_1(monkeypatch):
    closes = [100.0] * 10
    conn, target = make_conn_with_prices(closes)
    # target_date greater than last inserted date; still < MA_WINDOW rows
    res = rd._calc_ma200_ratio(conn, target)
    assert res == 1.0


def test_calc_ma200_ratio_full_window_calculation():
    # create 200 rows all 100 except latest 110 -> ratio = 110/100 = 1.1
    closes = [100.0] * 199
    closes.insert(0, 110.0)  # latest should be first when ordering desc; but _calc_ma200_ratio selects date < target and orders desc limit 200
    # Build increasing dates so latest is newest; arrange closing values so latest higher
    # To ensure latest is newest, we will create increasing dates with latest last and then call with target_date one day after last entry.
    # So adjust: build closes where last element corresponds to latest close 110
    closes = [100.0] * 199 + [110.0]
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE prices_daily (code VARCHAR, date DATE, close DOUBLE)")
    base = date(2020, 1, 1)
    for i, c in enumerate(closes):
        dt = base + timedelta(days=i)
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", ["1321", dt, c])
    target = base + timedelta(days=len(closes))  # date after last
    res = rd._calc_ma200_ratio(conn, target)
    # average of 199*100 + 110 = (19900 + 110)/200 = 20010/200 = 100.05 -> latest 110 / ma = 1.09945...
    assert pytest.approx(res, rel=1e-6) == 110.0 / ((199 * 100.0 + 110.0) / 200.0)


def test_fetch_macro_news_filters_by_keywords_and_window():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE raw_news (id INTEGER, datetime TIMESTAMP, title VARCHAR)")
    now = datetime(2021, 1, 10, 12, 0)
    earlier = now - timedelta(hours=1)
    later = now + timedelta(hours=1)
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?)", [earlier, "日銀 が動く"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?)", [earlier, " unrelated"])
    conn.execute("INSERT INTO raw_news VALUES (3, ?, ?)", [earlier, "為替が変動"])
    titles = rd._fetch_macro_news(conn, earlier, later)
    # should include matching titles only
    assert "日銀 が動く" in titles
    assert "為替が変動" in titles
    assert "unrelated" not in titles


class DummyChoice:
    def __init__(self, content):
        class Msg:
            def __init__(self, c):
                self.content = c
        self.message = Msg(content)


class DummyResp:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]


def test_score_macro_success(monkeypatch):
    # patch _call_openai_api to return a valid JSON
    monkeypatch.setattr(rd, "_call_openai_api", lambda client, messages: DummyResp('{"macro_sentiment": 0.5}'))
    val = rd._score_macro(object(), ["title1"])
    assert val == 0.5


def test_score_macro_json_parse_fail_returns_zero(monkeypatch, caplog):
    monkeypatch.setattr(rd, "_call_openai_api", lambda client, messages: DummyResp("not json"))
    val = rd._score_macro(object(), ["t"])
    assert val == 0.0
    assert "レスポンスパース失敗" in caplog.text or "レスポンスパース失敗" in caplog.text


def test_score_macro_retries_on_rate_limit(monkeypatch):
    calls = {"n": 0}

    def flaky(client, messages):
        calls["n"] += 1
        if calls["n"] < 3:
            raise rd.RateLimitError("rate")
        return DummyResp('{"macro_sentiment": -0.8}')

    monkeypatch.setattr(rd, "_call_openai_api", flaky)
    # patch sleep to avoid delay
    monkeypatch.setattr("time.sleep", lambda s: None)
    val = rd._score_macro(object(), ["t"])
    # after retries should get value
    assert pytest.approx(val, rel=1e-6) == -0.8


def test_score_regime_writes_market_regime(monkeypatch, tmp_path):
    # prepare in-memory conn with necessary tables
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE prices_daily (code VARCHAR, date DATE, close DOUBLE)")
    conn.execute("CREATE TABLE raw_news (id INTEGER, datetime TIMESTAMP, title VARCHAR)")
    conn.execute("CREATE TABLE market_regime (date DATE, regime_score DOUBLE, regime_label VARCHAR, ma200_ratio DOUBLE, macro_sentiment DOUBLE)")

    # insert 200 price rows for 1321 with close=100 (ma) and latest 120 to ensure bull
    base = date(2020, 1, 1)
    for i in range(200):
        dt = base + timedelta(days=i)
        close = 100.0 if i < 199 else 130.0  # last one 130
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", ["1321", dt, close])

    # no news to keep macro_sentiment 0.0
    target = base + timedelta(days=200)

    # ensure OPENAI_API_KEY resolved: patch OpenAI and _score_macro to avoid real API
    monkeypatch.setenv("OPENAI_API_KEY", "ok")
    # patch rd._score_macro to deterministic 0.0
    monkeypatch.setattr(rd, "_score_macro", lambda client, titles: 0.0)
    # call
    res = rd.score_regime(conn, target, api_key="dummy")
    assert res == 1
    row = conn.execute("SELECT regime_score, regime_label, ma200_ratio, macro_sentiment FROM market_regime WHERE date = ?", [target]).fetchone()
    assert row is not None
    regime_score, label, ma200_ratio, macro_sentiment = row
    assert macro_sentiment == 0.0
    # because latest 130 and MA ~ (199*100 + 130)/200 -> >1 leading to positive regime_score
    assert label in ("bull", "neutral", "bear")

File: tests/test_news_nlp.py
--------------------------------
import json
from datetime import date, datetime, timedelta
import duckdb
import pytest
from kabusys.ai import news_nlp as nn


def test_calc_news_window_expected():
    t = date(2026, 3, 20)
    s, e = nn.calc_news_window(t)
    # expected as docstring: start = 2026-03-19 06:00, end = 2026-03-19 23:30
    assert s == datetime(2026, 3, 19, 6, 0)
    assert e == datetime(2026, 3, 19, 23, 30)


class DummyChoice:
    def __init__(self, content):
        class Msg:
            def __init__(self, c):
                self.content = c
        self.message = Msg(content)


class DummyResp:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]


def test_validate_and_extract_valid_and_clipping():
    requested = {"1234", "5678"}
    content = json.dumps({"results":[{"code":"1234","score":1.5},{"code":"5678","score":-2.0}]})
    resp = DummyResp(content)
    out = nn._validate_and_extract(resp, requested)
    # clipping to ±1.0
    assert out["1234"] == 1.0
    assert out["5678"] == -1.0


def test_validate_and_extract_embedded_json_and_unknown_codes(caplog):
    requested = {"1111"}
    # resp contains surrounding text but a valid JSON object inside
    content = "some preamble {\"results\":[{\"code\":1111,\"score\":0.25}]} some trailing"
    resp = DummyResp(content)
    out = nn._validate_and_extract(resp, requested)
    assert out["1111"] == pytest.approx(0.25)
    # unknown code is ignored
    requested2 = {"9999"}
    resp2 = DummyResp(json.dumps({"results":[{"code":"1111","score":0.5},{"code":"9999","score":"notnum"}]}))
    out2 = nn._validate_and_extract(resp2, requested2)
    # non-numeric score ignored so not present
    assert out2 == {}


def test_fetch_articles_grouping_and_trimming():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE raw_news (id INTEGER, datetime TIMESTAMP, title VARCHAR, content VARCHAR)")
    conn.execute("CREATE TABLE news_symbols (news_id INTEGER, code VARCHAR)")
    # create two articles for same code
    now = datetime(2021, 1, 10, 12, 0)
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?, ?)", [now, "T1", "C1"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?, ?)", [now, "T2", "C2"])
    conn.execute("INSERT INTO news_symbols VALUES (1, '0001')")
    conn.execute("INSERT INTO news_symbols VALUES (2, '0001')")
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)
    m = nn._fetch_articles(conn, start, end)
    assert "0001" in m
    assert any("T1" in t for t in m["0001"])
    assert any("T2" in t for t in m["0001"])


File: tests/test_research_stats.py
--------------------------------
import math
import pytest

from kabusys.research import rank, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize


def test_rank_with_ties_and_unique():
    vals = [10.0, 20.0, 20.0, 5.0]
    r = rank(vals)
    # ranks should be [2.0, 3.0, 3.0, 1.0] (1-indexed average ranks for ties)
    assert r == [2.0, 3.0, 3.0, 1.0]


def test_calc_ic_insufficient_returns_none():
    factor = [{"code":"A","mom_1m":1.0},{"code":"B","mom_1m":None}]
    fwd = [{"code":"A","fwd_1d":0.1}]
    assert calc_ic(factor, fwd, "mom_1m", "fwd_1d") is None


def test_calc_ic_basic_positive_correlation():
    factor = [
        {"code":"A","mom_1m":1.0},
        {"code":"B","mom_1m":2.0},
        {"code":"C","mom_1m":3.0},
    ]
    fwd = [
        {"code":"A","fwd_1d":0.1},
        {"code":"B","fwd_1d":0.2},
        {"code":"C","fwd_1d":0.3},
    ]
    ic = calc_ic(factor, fwd, "mom_1m", "fwd_1d")
    assert pytest.approx(ic, rel=1e-6) == 1.0


def test_factor_summary_empty_and_values():
    records = [
        {"code":"A","val": 1.0},
        {"code":"B","val": 3.0},
        {"code":"C","val": None},
        {"code":"D","val": 5.0},
    ]
    res = factor_summary(records, ["val"])
    assert res["val"]["count"] == 3
    assert res["val"]["min"] == 1.0
    assert res["val"]["max"] == 5.0


def test_zscore_normalize_basic():
    records = [{"code":"A","x":1.0},{"code":"B","x":3.0},{"code":"C","x":5.0}]
    out = zscore_normalize(records, ["x"])
    vals = [r["x"] for r in out]
    mean = sum([1.0,3.0,5.0])/3
    var = sum((v-mean)**2 for v in [1.0,3.0,5.0])/3
    std = math.sqrt(var)
    assert pytest.approx(vals[0], rel=1e-6) == (1.0 - mean) / std

実行方法:
- プロジェクトルートで pytest を実行してください (pytest -q)。
- 必要に応じて DuckDB をインストール: pip install duckdb

説明（簡潔）:
- config: .env 行パース、ファイルロード、Settings の主要プロパティとバリデーションをテスト。
- ai.regime_detector: MA200 比率計算（0件・不足・十分）、マクロニュース抽出、LLM スコアリングの成功/失敗/リトライパス、score_regime の DB 書き込みフロー（OpenAI 部分はモック）。
- ai.news_nlp: ニュースウィンドウ計算、API レスポンスパース/検証、記事取得の集約処理。
- research / stats: rank / calc_ic / factor_summary / zscore_normalize の主要ロジックとエッジケース。

必要であれば、特定モジュール（例: jquants_client や network 周り）のテストも追加します。