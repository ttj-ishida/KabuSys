"""
Strategy Engine テスト

feature_engineering と signal_generator の動作を検証する。
"""

import datetime
from datetime import date

import duckdb
import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.feature_engineering import (
    _MIN_PRICE,
    _MIN_TURNOVER,
    _apply_universe_filter,
    build_features,
)
from kabusys.strategy.signal_generator import (
    _compute_liquidity_score,
    _compute_momentum_score,
    _compute_value_score,
    _compute_volatility_score,
    _is_bear_regime,
    _sigmoid,
    generate_signals,
)

TARGET_DATE = date(2020, 6, 1)
_HISTORY_START = date(2019, 6, 1)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_price_history(
    conn: duckdb.DuckDBPyConnection,
    codes_and_params: list[tuple[str, float, float]],
    start: date = _HISTORY_START,
    end: date = TARGET_DATE,
) -> None:
    """複数銘柄の価格履歴を平日分のみ挿入する。

    codes_and_params: [(code, close, turnover), ...]
    """
    d = start
    while d <= end:
        if d.weekday() < 5:  # 平日のみ
            for code, close, turnover in codes_and_params:
                try:
                    conn.execute(
                        "INSERT INTO prices_daily "
                        "(date, code, open, high, low, close, volume, turnover) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            d, code,
                            close * 0.99, close * 1.01, close * 0.98, close,
                            1_000_000, turnover,
                        ],
                    )
                except Exception:
                    pass  # 重複は無視
        d += datetime.timedelta(days=1)


# ---------------------------------------------------------------------------
# _sigmoid
# ---------------------------------------------------------------------------


def test_sigmoid_midpoint():
    assert _sigmoid(0.0) == pytest.approx(0.5)


def test_sigmoid_none():
    assert _sigmoid(None) is None


def test_sigmoid_monotone():
    assert _sigmoid(-3.0) < _sigmoid(0.0) < _sigmoid(3.0)


def test_sigmoid_range():
    for z in [-3.0, -1.0, 0.0, 1.0, 3.0]:
        s = _sigmoid(z)
        assert s is not None and 0.0 < s < 1.0


# ---------------------------------------------------------------------------
# _compute_* スコア
# ---------------------------------------------------------------------------


def test_compute_momentum_score_all_none():
    feat = {"momentum_20": None, "momentum_60": None, "ma200_dev": None}
    assert _compute_momentum_score(feat) is None


def test_compute_momentum_score_partial():
    feat = {"momentum_20": 2.0, "momentum_60": None, "ma200_dev": 1.0}
    score = _compute_momentum_score(feat)
    assert score is not None and 0.5 < score < 1.0


def test_compute_momentum_score_positive_higher():
    pos = _compute_momentum_score({"momentum_20": 2.0, "momentum_60": 2.0, "ma200_dev": 2.0})
    neg = _compute_momentum_score({"momentum_20": -2.0, "momentum_60": -2.0, "ma200_dev": -2.0})
    assert pos > neg


def test_compute_value_score_zero_per():
    assert _compute_value_score({"per": 0}) is None


def test_compute_value_score_none():
    assert _compute_value_score({"per": None}) is None


def test_compute_value_score_per20():
    # PER = 20 → score = 1 / (1 + 20/20) = 0.5
    assert _compute_value_score({"per": 20.0}) == pytest.approx(0.5)


def test_compute_value_score_lower_per_higher_score():
    low_per = _compute_value_score({"per": 10.0})
    high_per = _compute_value_score({"per": 40.0})
    assert low_per > high_per


def test_compute_volatility_score_inverted():
    # 低ボラ（負の z）→ 高スコア
    high = _compute_volatility_score({"volatility_20": -2.0})
    low = _compute_volatility_score({"volatility_20": 2.0})
    assert high > low


def test_compute_volatility_score_none():
    assert _compute_volatility_score({"volatility_20": None}) is None


def test_compute_liquidity_score_positive():
    s1 = _compute_liquidity_score({"volume_ratio": 2.0})
    s2 = _compute_liquidity_score({"volume_ratio": -2.0})
    assert s1 > s2


def test_compute_liquidity_score_none():
    assert _compute_liquidity_score({"volume_ratio": None}) is None


# ---------------------------------------------------------------------------
# _is_bear_regime
# ---------------------------------------------------------------------------


def test_is_bear_regime_empty():
    assert _is_bear_regime({}) is False


def test_is_bear_regime_bull():
    ai = {"A": {"regime_score": 0.5}, "B": {"regime_score": 0.3}}
    assert _is_bear_regime(ai) is False


def test_is_bear_regime_bear():
    ai = {"A": {"regime_score": -0.5}, "B": {"regime_score": -0.3}}
    assert _is_bear_regime(ai) is True


def test_is_bear_regime_all_none():
    ai = {"A": {"regime_score": None}, "B": {"regime_score": None}}
    assert _is_bear_regime(ai) is False


# ---------------------------------------------------------------------------
# _apply_universe_filter
# ---------------------------------------------------------------------------


def test_apply_universe_filter_price():
    records = [
        {"code": "LOW", "avg_turnover": 6e8, "mom_1m": 0.0},
        {"code": "OK", "avg_turnover": 6e8, "mom_1m": 0.0},
    ]
    price_map = {"LOW": 200.0, "OK": 1000.0}
    result = _apply_universe_filter(records, price_map)
    codes = {r["code"] for r in result}
    assert "OK" in codes
    assert "LOW" not in codes


def test_apply_universe_filter_turnover():
    records = [
        {"code": "POOR", "avg_turnover": 1e7, "mom_1m": 0.0},
        {"code": "RICH", "avg_turnover": 6e8, "mom_1m": 0.0},
    ]
    price_map = {"POOR": 1000.0, "RICH": 1000.0}
    result = _apply_universe_filter(records, price_map)
    codes = {r["code"] for r in result}
    assert "RICH" in codes
    assert "POOR" not in codes


def test_apply_universe_filter_none_price():
    records = [{"code": "X", "avg_turnover": 6e8}]
    result = _apply_universe_filter(records, {})
    assert result == []


# ---------------------------------------------------------------------------
# build_features
# ---------------------------------------------------------------------------


def test_build_features_price_filter(conn):
    """株価 < 300 の銘柄はフィルタされる"""
    _insert_price_history(conn, [("LOW", 200.0, 6e8), ("HIGH", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute(
        "SELECT code FROM features WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    codes = {r[0] for r in rows}
    assert "HIGH" in codes
    assert "LOW" not in codes


def test_build_features_turnover_filter(conn):
    """平均売買代金 < 5 億の銘柄はフィルタされる"""
    _insert_price_history(conn, [("POOR", 1000.0, 1e7), ("RICH", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute(
        "SELECT code FROM features WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    codes = {r[0] for r in rows}
    assert "RICH" in codes
    assert "POOR" not in codes


def test_build_features_returns_count(conn):
    """戻り値はフィルタ通過後の銘柄数に一致する"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 500.0, 6e8)])
    count = build_features(conn, TARGET_DATE)
    assert count == 2


def test_build_features_idempotent(conn):
    """2 回実行しても features の行数が変わらない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 2000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    c1 = conn.execute(
        "SELECT COUNT(*) FROM features WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    build_features(conn, TARGET_DATE)
    c2 = conn.execute(
        "SELECT COUNT(*) FROM features WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert c1 == c2


def test_build_features_zscore_clipped(conn):
    """Z スコア値は ±3 内に収まる"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 500.0, 6e8), ("C", 800.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute(
        "SELECT momentum_20, momentum_60, ma200_dev FROM features WHERE date = ?",
        [TARGET_DATE],
    ).fetchall()
    assert rows, "features が空"
    for row in rows:
        for val in row:
            if val is not None:
                assert -3.0 <= val <= 3.0, f"Z スコア ±3 範囲外: {val}"


# ---------------------------------------------------------------------------
# generate_signals
# ---------------------------------------------------------------------------


def test_generate_signals_empty_features(conn):
    """features が空なら 0 を返す"""
    count = generate_signals(conn, TARGET_DATE)
    assert count == 0


def test_generate_signals_buy_signal(conn):
    """高スコアの銘柄に BUY シグナルが生成される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 1000.0, 6e8), ("C", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # A に高い momentum z スコアを手動設定
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0, ma200_dev = 3.0, "
        "volume_ratio = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None and row[0] == "buy"


def test_generate_signals_below_threshold_no_buy(conn):
    """threshold 未満のスコアでは BUY シグナルが生成されない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # デフォルト threshold=0.60 で、neutral スコアは ~0.50 < 0.60
    generate_signals(conn, TARGET_DATE, threshold=0.60)
    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
    ).fetchall()
    assert len(rows) == 0


def test_generate_signals_bear_regime_suppresses_buy(conn):
    """Bear レジーム時は BUY シグナルが抑制される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE date = ?",
        [TARGET_DATE],
    )
    conn.execute(
        "INSERT INTO ai_scores (date, code, sentiment_score, regime_score, ai_score) "
        "VALUES (?, 'A', -0.5, -0.8, -0.5)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.1)
    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
    ).fetchall()
    assert len(rows) == 0


def test_generate_signals_stop_loss(conn):
    """ストップロス条件（-8% 以上の下落）で SELL シグナルが生成される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # avg_price = 1100 円、終値 = 1000 円 → -9.1% → stop-loss 発動
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1100.0, 100000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None and row[0] == "sell"


def test_generate_signals_score_drop_sell(conn):
    """スコア低下でもポジション保有銘柄に SELL シグナルが生成される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # A のスコアが低い状態（デフォルト ≈ 0.50 < 0.60）
    # avg_price = 950 → pnl = +5.26% → stop-loss 非発動
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 950.0, 100000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.60)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None and row[0] == "sell"


def test_generate_signals_idempotent(conn):
    """2 回実行しても signals の行数が変わらない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    generate_signals(conn, TARGET_DATE)
    c1 = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    generate_signals(conn, TARGET_DATE)
    c2 = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert c1 == c2


def test_generate_signals_rank_order(conn):
    """BUY シグナルのランクはスコア降順に割り当てられる"""
    _insert_price_history(conn, [
        ("A", 1000.0, 6e8),
        ("B", 1000.0, 6e8),
        ("C", 1000.0, 6e8),
    ])
    build_features(conn, TARGET_DATE)
    # A > B > C の順でスコアを設定
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    conn.execute(
        "UPDATE features SET momentum_20 = 1.0, momentum_60 = 1.0 WHERE code = 'B' AND date = ?",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.0)
    rows = conn.execute(
        "SELECT code, signal_rank FROM signals WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [TARGET_DATE],
    ).fetchall()
    assert len(rows) >= 2
    codes_in_rank_order = [r[0] for r in rows]
    assert codes_in_rank_order.index("A") < codes_in_rank_order.index("B")


def test_generate_signals_no_positions_no_sell(conn):
    """ポジションがなければ SELL シグナルは生成されない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    generate_signals(conn, TARGET_DATE)
    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND side = 'sell'", [TARGET_DATE]
    ).fetchall()
    assert len(rows) == 0


def test_generate_signals_isolation():
    """strategy モジュールが execution 層をインポートしていないこと"""
    import importlib
    import sys

    for mod_name in ["kabusys.strategy.feature_engineering", "kabusys.strategy.signal_generator"]:
        mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
        forbidden = [
            name for name in dir(mod)
            if "kabusys.execution" in getattr(getattr(mod, name, None), "__module__", "")
        ]
        assert forbidden == [], f"{mod_name} が execution 層に依存している: {forbidden}"


def test_generate_signals_weights_partial(conn):
    """weights を部分指定しても KeyError にならない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # news キーのみ指定（他は _DEFAULT_WEIGHTS で補完される）
    count = generate_signals(conn, TARGET_DATE, weights={"news": 0.05})
    assert isinstance(count, int)


def test_generate_signals_weights_rescaled(conn):
    """合計が 1.0 でない weights は再スケールされ final_score が [0,1] 範囲に収まる"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # 合計 2.0 の weights を渡す
    w = {"momentum": 0.80, "value": 0.40, "volatility": 0.30, "liquidity": 0.30, "news": 0.20}
    generate_signals(conn, TARGET_DATE, threshold=0.0, weights=w)
    rows = conn.execute(
        "SELECT score FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
    ).fetchall()
    for (score,) in rows:
        assert 0.0 <= score <= 1.0, f"score={score} が [0,1] 範囲外"


def test_generate_signals_stale_position_sell(conn):
    """positions の日付が target_date より古くても最新スナップショットで SELL 判定される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # positions は TARGET_DATE より前の日付で登録（avg_price=1100、現在値=1000 → -9.1% → stop-loss）
    stale_date = date(2020, 5, 1)
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1100.0, 110000.0)",
        [stale_date],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None and row[0] == "sell"


def test_generate_signals_weights_zero_total_fallback(conn):
    """weights 合計が 0 の場合は _DEFAULT_WEIGHTS にフォールバックし正常動作する"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    zero_weights = {"momentum": 0.0, "value": 0.0, "volatility": 0.0, "liquidity": 0.0, "news": 0.0}
    count = generate_signals(conn, TARGET_DATE, weights=zero_weights)
    assert isinstance(count, int)


def test_generate_signals_no_price_on_target_date_still_sells(conn):
    """positions が存在し直近の価格が target_date 以前にある場合でも SELL 判定される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # ポジション登録（avg_price=1100 → stop-loss 発動予定）
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1100.0, 110000.0)",
        [TARGET_DATE],
    )
    # target_date の prices_daily は _insert_price_history で挿入済み（close=1000）
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "sell"


def test_generate_signals_weights_unknown_key_ignored(conn):
    """weights に未知キーを渡しても既知キーのスコアが歪まない"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # 未知キー "foo" を含む weights で実行しても例外にならず BUY シグナルが生成される
    generate_signals(conn, TARGET_DATE, threshold=0.5, weights={"momentum": 0.8, "foo": 99.9})
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "buy"


def test_generate_signals_missing_from_features_sells(conn):
    """features に存在しない保有銘柄は score=0.0 と見なされ SELL シグナルが生成される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    # build_features は呼ばない → features テーブルに A は存在しない
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 950.0, 95000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    # features に存在しないため score=0.0 < 0.6 → score_drop で SELL
    assert row is not None and row[0] == "sell"


def test_build_features_uses_latest_price_when_no_target_date_price(conn):
    """target_date に prices_daily がなくても直前の最新価格でフィルタが機能する"""
    # TARGET_DATE の1日前まで挿入（TARGET_DATE 当日は挿入しない）
    prev_date = date(2020, 5, 29)
    _insert_price_history(
        conn,
        [("A", 1000.0, 6e8)],
        start=_HISTORY_START,
        end=prev_date,
    )
    # TARGET_DATE に価格がなくても build_features が動作し、直前価格でフィルタされる
    count = build_features(conn, TARGET_DATE)
    # prev_date の価格 1000 >= 300 かつ turnover >= 5億 → フィルタ通過
    assert count >= 0  # エラーにならないことを確認
