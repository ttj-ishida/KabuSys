
import math
from datetime import date, datetime
from unittest import mock

import pytest

# config module
from kabusys.config import _parse_env_line, _require, Settings

# portfolio builder / risk / position sizing
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier
from kabusys.portfolio.position_sizing import calc_position_sizes

# feature engineering (universe filter)
from kabusys.research.feature_engineering import _apply_universe_filter

# signal generator utilities
from kabusys.strategy.signal_generator import (
    _sigmoid,
    _avg_scores,
    _generate_sell_signals,
)

# research utilities
from kabusys.research.feature_exploration import rank, calc_ic, factor_summary

# backtest simulator
from kabusys.backtest.simulator import PortfolioSimulator, DailySnapshot, TradeRecord

# news utilities
from kabusys.data.news import (
    _normalize_url,
    _make_article_id,
    _validate_url_scheme,
    _is_private_host,
    preprocess_text,
    _parse_rss_datetime,
)


# -------------------------
# config._parse_env_line
# -------------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    # inline comment is recognized only if preceded by space/tab
    assert _parse_env_line("KEY=val #comment") == ("KEY", "val")
    # hash immediately after value is part of value
    assert _parse_env_line("KEY=val#notcomment") == ("KEY", "val#notcomment")
    # export prefix
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    # quoted with escaped quote
    assert _parse_env_line(r"Q='a\'b'") == ("Q", "a'b")
    # double quoted with backslash escape for double quote
    assert _parse_env_line(r'Q2="a\"b"') == ("Q2", 'a"b')
    # empty or comment line returns None
    assert _parse_env_line("") is None
    assert _parse_env_line("# comment") is None
    # missing separator
    assert _parse_env_line("NOSEP") is None
    # missing key after export
    assert _parse_env_line("export =value") is None


# -------------------------
# Settings and _require
# -------------------------
def test_require_and_settings_properties(monkeypatch):
    # Ensure _require raises when missing
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        _require("JQUANTS_REFRESH_TOKEN")

    # set env and verify Settings properties
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "rtok")
    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "sbot")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "chid")
    monkeypatch.setenv("KABUSYS_ENV", "live")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    s = Settings()
    assert s.jquants_refresh_token == "rtok"
    assert s.kabu_api_password == "pwd"
    assert s.slack_bot_token == "sbot"
    assert s.slack_channel_id == "chid"
    assert s.env == "live"
    assert s.log_level == "DEBUG"
    assert s.is_live is True
    assert s.is_paper is False
    assert s.is_dev is False

    # env invalid value raises
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    monkeypatch.setenv("LOG_LEVEL", "NOPE")
    with pytest.raises(ValueError):
        _ = s.log_level


# -------------------------
# Portfolio builder
# -------------------------
def test_select_candidates_and_weights():
    signals = [
        {"code": "A", "score": 1.0},
        {"code": "B", "score": 2.0},
        {"code": "C", "score": 0.5},
    ]
    top2 = select_candidates(signals, max_positions=2)
    assert [s["code"] for s in top2] == ["B", "A"]

    # empty input
    assert select_candidates([], 5) == []

    # equal weights
    eq = calc_equal_weights([{"code": "A"}, {"code": "B"}, {"code": "C"}])
    assert math.isclose(eq["A"], 1.0 / 3)
    assert sum(eq.values()) == pytest.approx(1.0)

    # score weights normal
    sc = calc_score_weights([{"code": "A", "score": 1.0}, {"code": "B", "score": 3.0}])
    assert sc["A"] == pytest.approx(1.0 / 4.0)
    assert sc["B"] == pytest.approx(3.0 / 4.0)

def test_calc_score_weights_all_zero_fallback(caplog):
    caplog.clear()
    caplog.set_level("WARNING")
    candidates = [{"code": "A", "score": 0.0}, {"code": "B", "score": 0.0}]
    w = calc_score_weights(candidates)
    # fallback equal weights
    assert w == {"A": 0.5, "B": 0.5}
    # warning emitted
    assert any("等金額配分にフォールバック" in rec.message or "フォールバック" in rec.message for rec in caplog.records)


# -------------------------
# risk_adjustment
# -------------------------
def test_apply_sector_cap_filters_blocked_sector(caplog):
    caplog.set_level("DEBUG")
    candidates = [{"code": "B", "score": 1.0}, {"code": "C", "score": 0.5}]
    sector_map = {"A": "tech", "B": "tech", "C": "other"}
    current_positions = {"A": 100}  # large exposure for tech
    open_prices = {"A": 2.0, "B": 10.0, "C": 5.0}
    portfolio_value = 1000.0
    # exposure for tech = 100 * 2 = 200 => 200/1000 = 0.2 > default 0.3? default is 0.30 -> 0.2 not exceed
    # choose smaller max_sector_pct to trigger
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, open_prices, max_sector_pct=0.1)
    # B is in same sector 'tech' and should be filtered out
    assert filtered == [{"code": "C", "score": 0.5}]
    assert any("除外" in rec.message or "上限" in rec.message for rec in caplog.records)

def test_calc_regime_multiplier_and_unknown_logs(caplog):
    caplog.set_level("WARNING")
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    # unknown -> warning + fallback 1.0
    caplog.clear()
    assert calc_regime_multiplier("mystery") == 1.0
    assert any("未知のレジーム" in r.message or "フォールバック" in r.message for r in caplog.records)


# -------------------------
# position_sizing
# -------------------------
def test_calc_position_sizes_equal_and_scaling():
    weights = {"A": 0.5, "B": 0.5}
    candidates = [{"code": "A"}, {"code": "B"}]
    portfolio_value = 1_000_000.0
    available_cash = 150_000.0  # less than raw plan cost to force scaling
    current_positions = {}
    open_prices = {"A": 1000.0, "B": 1000.0}
    sized = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=portfolio_value,
        available_cash=available_cash,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="equal",
        lot_size=10,
    )
    # raw target per stock would be capped to _max_per_stock floor(1e6*0.1/1000)=100 shares each -> raw cost=200*1000=200000
    # scale = 150000/200000 = 0.75 => new_shares floor(100*0.75)=75 -> rounded down to nearest 10 => 70
    assert sized == {"A": 70, "B": 70}

def test_calc_position_sizes_risk_based_lot_and_skips():
    candidates = [{"code": "X"}]
    weights = {}
    portfolio_value = 1_000_000.0
    available_cash = 10000.0
    current_positions = {}
    open_prices = {"X": 1000.0}
    # use lot_size=1 to allow non-zero target_shares
    sized = calc_position_sizes(
        weights=weights,
        candidates=candidates,
        portfolio_value=portfolio_value,
        available_cash=available_cash,
        current_positions=current_positions,
        open_prices=open_prices,
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
        lot_size=1,
    )
    # base_shares = floor(portfolio_value * risk_pct / (price * stop_loss_pct))
    base_shares = math.floor(portfolio_value * 0.005 / (1000.0 * 0.08))
    assert sized.get("X", 0) == base_shares  # should produce expected shares


# -------------------------
# universe filter
# -------------------------
def test_apply_universe_filter_basic():
    recs = [
        {"code": "A", "avg_turnover": 6e8},  # price check uses price_map
        {"code": "B", "avg_turnover": 1e7},
        {"code": "C", "avg_turnover": 6e8},
    ]
    price_map = {"A": 500.0, "B": 100.0, "C": float("nan")}
    out = _apply_universe_filter(recs, price_map)
    # A passes, B fails price >= 300, C fails close nan
    assert out == [{"code": "A", "avg_turnover": 6e8}]


# -------------------------
# signal_generator utils
# -------------------------
def test_sigmoid_and_avg_scores_and_generate_sell_signals(tmp_path, monkeypatch, caplog):
    # _sigmoid
    assert _sigmoid(None) is None
    assert _sigmoid(0.0) == pytest.approx(0.5)
    assert _sigmoid(1000.0) == pytest.approx(1.0, rel=1e-6)
    # overflow path: large negative z
    assert _sigmoid(-1000.0) == pytest.approx(0.0)

    # _avg_scores
    assert _avg_scores([None, None]) is None
    assert _avg_scores([0.5, None, 1.5]) == pytest.approx(1.0)

    # _generate_sell_signals requires a duckdb connection and tables: we'll construct minimal duckdb in-memory
    import duckdb
    conn = duckdb.connect(database=":memory:")
    # create minimal schema for positions and prices_daily
    conn.execute("""
        CREATE TABLE positions (
            date DATE,
            code VARCHAR,
            position_size INTEGER,
            avg_price DOUBLE
        );
    """)
    conn.execute("""
        CREATE TABLE prices_daily (
            date DATE,
            code VARCHAR,
            close DOUBLE
        );
    """)
    target = date(2022, 1, 3)
    # one position with avg_price 100, position_size 10, price today 90 -> pnl_rate = -0.1 -> stop_loss
    conn.executemany("INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
                     [(target, "AAA", 10, 100.0)])
    conn.executemany("INSERT INTO prices_daily (date, code, close) VALUES (?, ?, ?)",
                     [(target, "AAA", 90.0)])
    score_map = {}  # missing feature -> treated as 0.0
    caplog.set_level("WARNING")
    sells = _generate_sell_signals(conn, target, score_map, threshold=0.6)
    assert len(sells) == 1
    assert sells[0]["code"] == "AAA"
    assert sells[0]["reason"] == "stop_loss"
    # when price missing: should skip SELL and log warning
    conn2 = duckdb.connect(database=":memory:")
    conn2.execute("CREATE TABLE positions (date DATE, code VARCHAR, position_size INTEGER, avg_price DOUBLE);")
    conn2.execute("CREATE TABLE prices_daily (date DATE, code VARCHAR, close DOUBLE);")
    conn2.executemany("INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
                      [(target, "BBB", 5, 10.0)])
    # no price for BBB -> generator should skip and warn
    caplog.clear()
    sells2 = _generate_sell_signals(conn2, target, {}, threshold=0.6)
    assert sells2 == []
    assert any("価格が取得できないため SELL 判定をスキップ" in r.message or "取得できない" in r.message for r in caplog.records)


# -------------------------
# research.rank / calc_ic / factor_summary
# -------------------------
def test_rank_and_calc_ic_and_summary():
    vals = [10.0, 10.0, 20.0]
    r = rank(vals)
    # two ties -> average ranks 1.5, 1.5, 3.0
    assert r == [1.5, 1.5, 3.0]

    # calc_ic: create factor_records and forward_records with inverse relationship -> rho negative
    factor_records = [
        {"code": "A", "f": 1.0},
        {"code": "B", "f": 2.0},
        {"code": "C", "f": 3.0},
    ]
    forward_records = [
        {"code": "A", "fwd": 3.0},
        {"code": "B", "fwd": 2.0},
        {"code": "C", "fwd": 1.0},
    ]
    rho = calc_ic(factor_records, forward_records, "f", "fwd")
    assert rho is not None
    assert rho < 0.0 and rho < -0.9  # near -1 for perfect inverse rank

    # insufficient samples returns None
    rho2 = calc_ic(factor_records[:2], forward_records[:2], "f", "fwd")
    assert rho2 is None

    # factor_summary
    records = [
        {"a": 1.0, "b": None},
        {"a": 2.0, "b": 0.5},
        {"a": 3.0, "b": 1.5},
    ]
    summary = factor_summary(records, ["a", "b", "c"])
    assert summary["a"]["count"] == 3
    assert summary["a"]["mean"] == pytest.approx(2.0)
    assert summary["b"]["count"] == 2
    assert summary["b"]["min"] == pytest.approx(0.5)
    assert summary["c"]["count"] == 0
    assert summary["c"]["mean"] is None


# -------------------------
# news utilities
# -------------------------
def test_news_url_normalize_and_id_and_validation_and_text_and_parse_datetime(monkeypatch):
    url = "HTTPS://Example.COM/path?utm_source=x&b=2&a=1#frag"
    norm = _normalize_url(url)
    # scheme/host lowercased, query sorted, utm_* removed, fragment removed
    assert norm.startswith("https://example.com/path")
    assert "utm_source" not in norm
    assert "#" not in norm
    # consistent id generation
    id1 = _make_article_id(url)
    id2 = _make_article_id(url)
    assert isinstance(id1, str) and len(id1) == 32
    assert id1 == id2

    # scheme validation
    with pytest.raises(ValueError):
        _validate_url_scheme("ftp://example.com/foo")

    # private host detection: localhost and private IPs should be private
    assert _is_private_host("127.0.0.1")
    # some unknown host that cannot be resolved should be treated as non-private (function returns False)
    # To avoid DNS dependence, pass None -> treated as private
    assert _is_private_host(None)

    # preprocess_text removes urls and normalizes spaces
    txt = "Hello  world\nvisit https://example.com/page?id=1 \n"
    assert preprocess_text(txt) == "Hello world visit"

    # parse rss datetime - valid RFC2822
    dt = _parse_rss_datetime("Mon, 01 Jan 2024 00:00:00 +0900")
    assert isinstance(dt, datetime)
    # parse invalid -> returns roughly now (datetime object)
    dt2 = _parse_rss_datetime("not a date")
    assert isinstance(dt2, datetime)


# -------------------------
# PortfolioSimulator
# -------------------------
def test_portfolio_simulator_buy_sell_mark_to_market(caplog):
    ps = PortfolioSimulator(initial_cash=10000.0)
    # history empty; default trade date fallback to 1970-01-01
    # buy with shares > 0 and price present
    signals = [{"code": "AAA", "side": "buy", "shares": 50}]
    open_prices = {"AAA": 100.0}
    ps.execute_orders(signals, open_prices, slippage_rate=0.01, commission_rate=0.001, trading_day=date(2022,1,1))
    # cost: entry_price = 100*(1+0.01)=101, cost=5050, commission ~5.05, total ~5055.05
    assert ps.positions["AAA"] == 50
    assert "AAA" in ps.cost_basis
    assert ps.trades and ps.trades[-1].side == "buy"
    # mark to market with missing price should warn and count price as 0
    caplog.set_level("WARNING")
    ps.mark_to_market(date(2022,1,1), close_prices={})
    assert ps.history[-1].portfolio_value == pytest.approx(ps.cash)  # stock value 0
    assert any("終値が取得できません" in r.message or "取得できません" in r.message for r in caplog.records)
    # now sell (close all)
    ps.execute_orders([{"code": "AAA", "side": "sell"}], {"AAA": 120.0}, slippage_rate=0.01, commission_rate=0.001, trading_day=date(2022,1,2))
    assert "AAA" not in ps.positions
    assert ps.trades[-1].side == "sell"
    assert ps.trades[-1].realized_pnl is not None
