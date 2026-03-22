
import math
import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

# 設定モジュール
from kabusys.config import _parse_env_line, _load_env_file

# 特徴量エンジニアリング
from kabusys.feature_engineering import _apply_universe_filter

# シグナル生成ユーティリティ
from kabusys.strategy.signal_generator import (
    _sigmoid,
    _avg_scores,
    _compute_value_score,
    _is_bear_regime,
    _generate_sell_signals,
)

# バックテストシミュレータ / メトリクス
from kabusys.backtest.simulator import PortfolioSimulator, DailySnapshot, TradeRecord
from kabusys.backtest.metrics import (
    _calc_cagr,
    _calc_sharpe,
    _calc_max_drawdown,
    _calc_win_rate,
    _calc_payoff_ratio,
)

# ニュース収集ユーティリティ
from kabusys.data.news_collector import (
    _normalize_url,
    _make_article_id,
    _validate_url_scheme,
    extract_stock_codes,
)

# J-Quants utils
from kabusys.jquants.client import _to_float, _to_int


# ------------------------------
# kabusys.config._parse_env_line
# ------------------------------
def test_parse_env_line_blank_and_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("   # another") is None


def test_parse_env_line_export_and_no_equal():
    assert _parse_env_line("export KEY=val") == ("KEY", "val")
    assert _parse_env_line("KEYNOEQUAL") is None


def test_parse_env_line_quoted_with_escapes_and_inline_comment():
    # double quoted with escaped quote and backslash
    line = r'QUOTED="value with \"quote\" and \\backslash" # inline comment'
    k, v = _parse_env_line(line)
    assert k == "QUOTED"
    assert 'quote' in v and 'backslash' in v

    # single quoted
    line2 = "SINGLE='a\\'b'  # comment"
    k2, v2 = _parse_env_line(line2)
    assert k2 == "SINGLE"
    assert "ab" in v2  # escaped apostrophe included


def test_parse_env_line_unquoted_inline_comment():
    assert _parse_env_line("K=val #this is comment") == ("K", "val")
    # when '#' not preceded by space should not be treated as comment
    assert _parse_env_line("K=hash#no_space") == ("K", "hash#no_space")


# ------------------------------
# kabusys.config._load_env_file
# ------------------------------
def test_load_env_file_tmpfile_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text("A=1\nB=2\nC=3\n")

    # start with B in os.environ
    monkeypatch.delenv("KABUSYS_DISABLE_AUTO_ENV_LOAD", raising=False)
    orig_env = dict(os.environ)
    try:
        os.environ.pop("A", None)
        os.environ["B"] = "orig"
        protected = frozenset(os.environ.keys())

        # load with override=False -> should not overwrite existing B
        _load_env_file(env_file, override=False, protected=protected)
        assert os.environ.get("A") == "1"
        assert os.environ.get("B") == "orig"

        # load with override=True protected contains B so B should remain orig
        os.environ["B"] = "orig2"
        _load_env_file(env_file, override=True, protected=protected)
        assert os.environ.get("B") == "orig2"

        # load with override=True and without protecting keys => overwrite
        _load_env_file(env_file, override=True, protected=frozenset())
        assert os.environ.get("B") == "2"
    finally:
        os.environ.clear()
        os.environ.update(orig_env)


# ------------------------------
# feature_engineering._apply_universe_filter
# ------------------------------
def test_apply_universe_filter_basic_and_edgecases():
    records = [
        {"code": "1000", "avg_turnover": 1e9},
        {"code": "2000", "avg_turnover": 1e9},
        {"code": "3000", "avg_turnover": 1e7},  # too small turnover
        {"code": "4000", "avg_turnover": None},
        {"code": "5000", "avg_turnover": 1e9},
    ]
    price_map = {
        "1000": 500.0,
        "2000": 100.0,         # price too low
        "3000": float("nan"),  # non-finite
        "5000": 1000.0,
    }
    filtered = _apply_universe_filter(records, price_map)
    codes = [r["code"] for r in filtered]
    assert "1000" in codes
    assert "5000" in codes
    assert "2000" not in codes
    assert "3000" not in codes
    assert "4000" not in codes


# ------------------------------
# strategy.signal_generator utilities
# ------------------------------
def test_sigmoid_and_avg_scores_and_value_score():
    assert _sigmoid(None) is None
    # typical values
    assert 0.5 - 1e-6 < _sigmoid(0.0) < 0.5 + 1e-6
    assert _sigmoid(10.0) > 0.999
    assert _sigmoid(-10.0) < 0.001

    assert _avg_scores([None, 0.5, 0.7]) == pytest.approx((0.5 + 0.7) / 2.0)
    assert _avg_scores([None, None]) is None

    # value score: per None or <=0 -> None
    assert _compute_value_score({"per": None}) is None
    assert _compute_value_score({"per": 0}) is None
    assert _compute_value_score({"per": 20}) == pytest.approx(0.5)


def test_is_bear_regime_thresholds():
    # less than min samples -> False
    ai_map = {"a": {"regime_score": -1.0}, "b": {"regime_score": 1.0}}
    assert _is_bear_regime(ai_map) is False

    # enough samples and negative average -> True
    ai_map2 = {"a": {"regime_score": -1.0}, "b": {"regime_score": -0.5}, "c": {"regime_score": -0.2}}
    assert _is_bear_regime(ai_map2) is True

    # positive average -> False
    ai_map3 = {"a": {"regime_score": 0.1}, "b": {"regime_score": 0.2}, "c": {"regime_score": 0.3}}
    assert _is_bear_regime(ai_map3) is False


def _make_conn_for_generate_sell_rows(rows_to_return):
    """
    Helper: create a mock conn whose execute(...).fetchall() returns rows_to_return
    for the sell query used in _generate_sell_signals. For other SQLs, return [].
    """
    conn = MagicMock()

    def execute_side_effect(sql, params=None):
        m = MagicMock()
        # detect the SELL query by presence of 'WITH latest_pos' snippet
        if "WITH latest_pos" in sql:
            m.fetchall.return_value = rows_to_return
        else:
            m.fetchall.return_value = []
        return m

    conn.execute.side_effect = execute_side_effect
    return conn


def test_generate_sell_signals_stop_loss_and_score_drop(caplog):
    target_date = date(2023, 1, 1)
    # rows: (code, avg_price, close)
    # code1: pnl below stop loss -> stop_loss
    # code2: pnl ok but not in score_map -> final_score 0 -> score_drop if threshold>0
    rows = [
        ("C1", 100.0, 90.0),  # -10% -> stop loss (threshold irrelevant)
        ("C2", 100.0, 95.0),  # -5% -> not stop loss -> score_drop if final_score<threshold
        ("C3", None, 120.0),  # invalid avg_price -> skip
        ("C4", 100.0, None),  # missing close -> skip entire SELL logic
    ]
    conn = _make_conn_for_generate_sell_rows(rows)
    score_map = {"C1": 0.2, "C2": 0.5}  # C2 below typical threshold 0.6
    sell = _generate_sell_signals(conn, target_date, score_map, threshold=0.6)
    codes = {s["code"]: s["reason"] for s in sell}
    assert codes["C1"] == "stop_loss"
    # C2 should be score_drop
    assert codes["C2"] == "score_drop"
    # C3 and C4 should be absent
    assert "C3" not in codes
    assert "C4" not in codes


# ------------------------------
# backtest.simulator basic ops
# ------------------------------
def test_portfolio_simulator_buy_sell_and_mark_to_market(tmp_path, caplog):
    sim = PortfolioSimulator(initial_cash=10000.0)
    today = date(2023, 1, 3)
    # ensure history has a snapshot day so trades get that date
    sim.history.append(DailySnapshot(date=today, cash=sim.cash, positions={}, portfolio_value=sim.cash))

    # BUY: missing open price -> skipped
    sim.execute_orders([{"code": "0001", "side": "buy", "alloc": 1000.0}], {}, slippage_rate=0.0, commission_rate=0.0)
    assert "0001" not in sim.positions

    # BUY: enough alloc to buy shares
    open_prices = {"0001": 100.0}
    sim.execute_orders([{"code": "0001", "side": "buy", "alloc": 500.0}], open_prices, slippage_rate=0.01, commission_rate=0.001)
    # entry price = 100 * 1.01 = 101 -> shares = floor(500/101) = 4
    assert sim.positions["0001"] == 4
    assert sim.cost_basis["0001"] > 0
    assert sim.cash < 10000.0
    assert sim.trades and sim.trades[-1].side == "buy"

    # SELL: with missing open price -> warning and skip
    sim.execute_orders([{"code": "0002", "side": "sell"}], {}, slippage_rate=0.0, commission_rate=0.0)
    # SELL proper for existing position
    sim.execute_orders([{"code": "0001", "side": "sell"}], {"0001": 120.0}, slippage_rate=0.005, commission_rate=0.001)
    assert "0001" not in sim.positions
    assert sim.trades and sim.trades[-1].side == "sell"
    # realized_pnl should be number
    assert sim.trades[-1].realized_pnl is not None

    # mark_to_market missing close -> warning and portfolio evaluated with zero for missing
    sim.positions["X"] = 10
    sim.cost_basis["X"] = 50.0
    caplog.clear()
    sim.mark_to_market(today, {})  # no close for X -> warning expected
    assert any("終値が取得できません" in rec.message or "取得できません" in rec.message for rec in caplog.records)
    last_snapshot = sim.history[-1]
    # portfolio_value == cash + 0 (since missing price)
    assert last_snapshot.portfolio_value == pytest.approx(sim.cash)


# ------------------------------
# backtest.metrics functions
# ------------------------------
def test_calc_metrics_functions_edgecases():
    # _calc_cagr
    # less than 2 snapshots -> 0
    assert _calc_cagr([DailySnapshot(date=date(2023,1,1), cash=0, positions={}, portfolio_value=1000.0)]) == 0.0

    # normal CAGR
    h = [
        DailySnapshot(date=date(2020,1,1), cash=0, positions={}, portfolio_value=100.0),
        DailySnapshot(date=date(2021,1,1), cash=0, positions={}, portfolio_value=200.0),
    ]
    cagr = _calc_cagr(h)
    assert cagr > 0

    # _calc_sharpe
    history = [
        DailySnapshot(date=date(2023,1,1), cash=0, positions={}, portfolio_value=100.0),
        DailySnapshot(date=date(2023,1,2), cash=0, positions={}, portfolio_value=110.0),
        DailySnapshot(date=date(2023,1,3), cash=0, positions={}, portfolio_value=105.0),
    ]
    sharpe = _calc_sharpe(history)
    assert sharpe >= 0.0

    # _calc_max_drawdown
    history2 = [
        DailySnapshot(date=date(2023,1,1), cash=0, positions={}, portfolio_value=100.0),
        DailySnapshot(date=date(2023,1,2), cash=0, positions={}, portfolio_value=150.0),
        DailySnapshot(date=date(2023,1,3), cash=0, positions={}, portfolio_value=90.0),
    ]
    md = _calc_max_drawdown(history2)
    assert 0.0 <= md <= 1.0

    # _calc_win_rate and payoff ratio
    trades = [
        TradeRecord(date=date(2023,1,2), code="A", side="sell", shares=1, price=0.0, commission=0.0, realized_pnl=10.0),
        TradeRecord(date=date(2023,1,3), code="B", side="sell", shares=1, price=0.0, commission=0.0, realized_pnl=-5.0),
        TradeRecord(date=date(2023,1,4), code="C", side="sell", shares=1, price=0.0, commission=0.0, realized_pnl=None),
    ]
    assert _calc_win_rate(trades) == pytest.approx(0.5)
    assert _calc_payoff_ratio(trades) == pytest.approx(10.0 / 5.0)


# ------------------------------
# news_collector utilities
# ------------------------------
def test_normalize_and_make_id_and_validate_scheme_and_extract_codes():
    url = "https://EXAMPLE.com/path?b=2&utm_source=x&a=1#frag"
    normalized = _normalize_url(url)
    assert "utm_source" not in normalized
    # query params sorted so a=1 before b=2
    assert "a=1" in normalized and "b=2" in normalized

    id1 = _make_article_id(url)
    id2 = _make_article_id(url)  # deterministic
    assert id1 == id2
    assert len(id1) == 32

    with pytest.raises(ValueError):
        _validate_url_scheme("ftp://example.com/resource")

    text = "This mentions 7203 and 7203 again and also 6758."
    codes = extract_stock_codes(text, known_codes={"7203", "6758", "1234"})
    assert codes == ["7203", "6758"]


# ------------------------------
# jquants client utils
# ------------------------------
def test_to_float_and_to_int_behaviour():
    assert _to_float(None) is None
    assert _to_float("1.5") == pytest.approx(1.5)
    assert _to_float("abc") is None

    assert _to_int(None) is None
    assert _to_int(2) == 2
    assert _to_int("2") == 2
    assert _to_int("2.0") == 2
    assert _to_int("2.5") is None
    assert _to_int("abc") is None
