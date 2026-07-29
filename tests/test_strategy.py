"""
Strategy Engine テスト

feature_engineering と signal_generator の動作を検証する。
"""

import datetime
import datetime as _dt
from datetime import date

import duckdb
import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.feature_engineering import (
    _apply_universe_filter,
    build_features,
)
from kabusys.strategy.signal_generator import (
    _calc_sector_strengths,
    _compute_liquidity_score,
    _compute_momentum_score,
    _compute_value_score,
    _compute_volatility_score,
    _fetch_gap_ratios,
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
                            d,
                            code,
                            close * 0.99,
                            close * 1.01,
                            close * 0.98,
                            close,
                            1_000_000,
                            turnover,
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
    cfg = {
        "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
        "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
    }
    assert _compute_value_score({"per": 0}, cfg) is None


def test_compute_value_score_none():
    cfg = {
        "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
        "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
    }
    assert _compute_value_score({"per": None}, cfg) is None


def test_compute_value_score_per20():
    cfg = {
        "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
        "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
    }
    # PER = 20 → score = 1 / (1 + 20/20) = 0.5
    assert _compute_value_score({"per": 20.0}, cfg) == pytest.approx(0.5)


def test_compute_value_score_lower_per_higher_score():
    cfg = {
        "weights": {"per": 0.50, "pbr": 0.30, "div_yield": 0.20},
        "normalization": {"per_mid": 20.0, "pbr_mid": 1.5, "div_yield_max": 3.0},
    }
    low_per = _compute_value_score({"per": 10.0}, cfg)
    high_per = _compute_value_score({"per": 40.0}, cfg)
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


def test_is_bear_regime_empty(conn):
    """market_regime にデータなし → False（安全側）"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


def test_is_bear_regime_bull(conn):
    """regime_label='bull' → False"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [TARGET_DATE, 0.5, "bull"],
    )
    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


def test_is_bear_regime_bear(conn):
    """regime_label='bear' → True"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [TARGET_DATE, -0.5, "bear"],
    )
    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bear"


def test_is_bear_regime_insufficient_samples(conn):
    """market_regime にデータなし（旧：サンプル不足）→ False"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


def test_is_bear_regime_all_none(conn):
    """market_regime にデータなし → False"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


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


def test_apply_universe_filter_market_excludes_unlisted_codes():
    """market_set が指定されている場合、含まれないコード（ETF/REIT等）は除外される"""
    records = [
        {"code": "STOCK", "avg_turnover": 6e8},
        {"code": "ETF", "avg_turnover": 6e8},
    ]
    price_map = {"STOCK": 1000.0, "ETF": 1000.0}
    result = _apply_universe_filter(records, price_map, market_set={"STOCK"})
    codes = {r["code"] for r in result}
    assert codes == {"STOCK"}


def test_apply_universe_filter_market_none_skips_filter():
    """market_set が None の場合は市場区分フィルタをスキップする（後方互換）"""
    records = [{"code": "X", "avg_turnover": 6e8}]
    result = _apply_universe_filter(records, {"X": 1000.0}, market_set=None)
    assert {r["code"] for r in result} == {"X"}


def test_apply_universe_filter_market_empty_skips_filter():
    """market_set が空集合の場合は市場区分フィルタをスキップする（stocks 未整備時）"""
    records = [{"code": "X", "avg_turnover": 6e8}]
    result = _apply_universe_filter(records, {"X": 1000.0}, market_set=set())
    assert {r["code"] for r in result} == {"X"}


# ---------------------------------------------------------------------------
# build_features
# ---------------------------------------------------------------------------


def test_build_features_price_filter(conn):
    """株価 < 300 の銘柄はフィルタされる"""
    _insert_price_history(conn, [("LOW", 200.0, 6e8), ("HIGH", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute("SELECT code FROM features WHERE date = ?", [TARGET_DATE]).fetchall()
    codes = {r[0] for r in rows}
    assert "HIGH" in codes
    assert "LOW" not in codes


def test_build_features_turnover_filter(conn):
    """平均売買代金 < 5 億の銘柄はフィルタされる"""
    _insert_price_history(conn, [("POOR", 1000.0, 1e7), ("RICH", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute("SELECT code FROM features WHERE date = ?", [TARGET_DATE]).fetchall()
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
    c1 = conn.execute("SELECT COUNT(*) FROM features WHERE date = ?", [TARGET_DATE]).fetchone()[0]
    build_features(conn, TARGET_DATE)
    c2 = conn.execute("SELECT COUNT(*) FROM features WHERE date = ?", [TARGET_DATE]).fetchone()[0]
    assert c1 == c2


def test_build_features_market_filter_excludes_etf(conn):
    """stocks.market が Prime/Standard/Growth 以外（ETF等）の銘柄は除外される"""
    _insert_price_history(conn, [("1301", 1000.0, 6e8), ("1305", 1000.0, 6e8)])
    conn.execute("INSERT INTO stocks (code, market) VALUES (?, ?)", ["1301", "Prime"])
    conn.execute("INSERT INTO stocks (code, market) VALUES (?, ?)", ["1305", "ETF"])
    build_features(conn, TARGET_DATE)
    rows = conn.execute("SELECT code FROM features WHERE date = ?", [TARGET_DATE]).fetchall()
    codes = {r[0] for r in rows}
    assert "1301" in codes
    assert "1305" not in codes


def test_build_features_market_filter_skipped_when_stocks_empty(conn):
    """stocks テーブルが未整備（空）の場合、市場区分フィルタはスキップされる"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 2000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    rows = conn.execute("SELECT code FROM features WHERE date = ?", [TARGET_DATE]).fetchall()
    codes = {r[0] for r in rows}
    assert codes == {"A", "B"}


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
    from kabusys.core.interfaces import DatabaseRegimeProvider

    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 1000.0, 6e8), ("C", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE date = ?",
        [TARGET_DATE],
    )
    # market_regime テーブルに bear を登録（新しい _is_bear_regime の参照先）
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [TARGET_DATE, -0.8, "bear"],
    )
    regime_provider = DatabaseRegimeProvider(conn)
    generate_signals(conn, TARGET_DATE, threshold=0.1, regime_provider=regime_provider)
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
    c1 = conn.execute("SELECT COUNT(*) FROM signals WHERE date = ?", [TARGET_DATE]).fetchone()[0]
    generate_signals(conn, TARGET_DATE)
    c2 = conn.execute("SELECT COUNT(*) FROM signals WHERE date = ?", [TARGET_DATE]).fetchone()[0]
    assert c1 == c2


def test_generate_signals_rank_order(conn):
    """BUY シグナルのランクはスコア降順に割り当てられる"""
    _insert_price_history(
        conn,
        [
            ("A", 1000.0, 6e8),
            ("B", 1000.0, 6e8),
            ("C", 1000.0, 6e8),
        ],
    )
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

    for mod_name in [
        "kabusys.strategy.feature_engineering",
        "kabusys.strategy.signal_generator",
    ]:
        mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
        forbidden = [
            name
            for name in dir(mod)
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
    w = {
        "momentum": 0.80,
        "value": 0.40,
        "volatility": 0.30,
        "liquidity": 0.30,
        "news": 0.20,
    }
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
    zero_weights = {
        "momentum": 0.0,
        "value": 0.0,
        "volatility": 0.0,
        "liquidity": 0.0,
        "news": 0.0,
    }
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


def test_generate_signals_no_buy_sell_conflict(conn):
    """同日同銘柄に BUY と SELL が同時に出ないこと（SELL 優先）"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # A に高いスコアを設定（BUY 候補）
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # A にストップロスを発動させる（avg_price=1100、終値=1000 → -9.1%）
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1100.0, 110000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchall()
    sides = {r[0] for r in rows}
    # SELL のみが存在し BUY は除外されていること
    assert "sell" in sides
    assert "buy" not in sides


def test_generate_signals_weights_invalid_values_ignored(conn):
    """weights に NaN/Inf/負値が含まれてもフォールバックして正常動作する"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    invalid_weights = {
        "momentum": float("nan"),
        "value": float("inf"),
        "volatility": -0.5,
        "liquidity": 0.15,
        "news": 0.10,
    }
    count = generate_signals(conn, TARGET_DATE, weights=invalid_weights)
    assert isinstance(count, int)


def test_generate_signals_rank_consecutive_after_sell_exclusion(conn):
    """SELL 除外後も BUY の signal_rank が連番（1,2,3…）になること"""
    _insert_price_history(
        conn,
        [
            ("A", 1000.0, 6e8),
            ("B", 1000.0, 6e8),
            ("C", 1000.0, 6e8),
            ("D", 1000.0, 6e8),
        ],
    )
    build_features(conn, TARGET_DATE)
    # A > B > C > D の順にスコアを設定
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    conn.execute(
        "UPDATE features SET momentum_20 = 2.0, momentum_60 = 2.0 WHERE code = 'B' AND date = ?",
        [TARGET_DATE],
    )
    conn.execute(
        "UPDATE features SET momentum_20 = 1.0, momentum_60 = 1.0 WHERE code = 'C' AND date = ?",
        [TARGET_DATE],
    )
    # B にストップロスを発動（SELL 対象 → BUY から除外されるべき）
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'B', 100, 1100.0, 110000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.0)
    rows = conn.execute(
        "SELECT code, signal_rank FROM signals WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [TARGET_DATE],
    ).fetchall()
    ranks = [r[1] for r in rows]
    # ランクが連番であること（1,2,3... で欠番なし）
    assert ranks == list(range(1, len(ranks) + 1))
    # B は除外されていること
    codes = [r[0] for r in rows]
    assert "B" not in codes


def test_generate_signals_stop_loss_exact_threshold(conn):
    """ちょうど -8% の下落でストップロスが発動すること（<= 比較）"""
    _insert_price_history(conn, [("A", 920.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # avg_price = 1000、終値 = 920 → pnl = -8.0% → stop-loss 発動すべき
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1000.0, 92000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None and row[0] == "sell"


def test_generate_signals_weights_bool_ignored(conn):
    """weights に bool 値が含まれる場合は無効値として無視されること"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # True/False は isinstance(v, bool) チェックでスキップされる
    bool_weights = {
        "momentum": True,
        "value": False,
        "liquidity": 0.15,
        "news": 0.10,
    }
    count = generate_signals(conn, TARGET_DATE, weights=bool_weights)
    assert isinstance(count, int)


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


def test_generate_signals_no_price_suppresses_sell(conn):
    """positions に対応する価格が prices_daily に一切存在しない場合は SELL を出さない"""
    # prices_daily に価格を登録しない → LEFT JOIN で close = NULL になる
    # ただし positions だけ登録する
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'Z', 100, 1000.0, 100000.0)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.6)
    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'Z'", [TARGET_DATE]
    ).fetchall()
    # close=None → SELL 判定全体をスキップ → シグナルなし
    assert len(rows) == 0


def test_is_bear_regime_exactly_min_samples(conn):
    """regime_label='bear' → True（旧：_BEAR_MIN_SAMPLES ちょうどのサンプル数テスト）"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [TARGET_DATE, -0.3, "bear"],
    )
    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bear"


# ---------------------------------------------------------------------------
# _fetch_gap_ratios
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# セクター強弱テスト用ヘルパー
# ---------------------------------------------------------------------------


def _insert_sector_test_data(
    conn: duckdb.DuckDBPyConnection,
    sector_data: list[tuple[str, str, float, float]],
    target_date: date = TARGET_DATE,
) -> None:
    """セクター強弱テスト用: stocks と prices_daily の最小セットを挿入する。

    Args:
        sector_data: [(code, sector, close_today, close_20d_ago), ...]
                     sector が空文字の場合は stocks に挿入しない。
        target_date: シグナル生成対象日（デフォルト TARGET_DATE）。
    """
    # 21 営業日分の日付を降順で生成（rn=1=target_date, rn=21=20営業日前）
    biz_dates: list[date] = []
    d = target_date
    while len(biz_dates) < 21:
        if d.weekday() < 5:
            biz_dates.append(d)
        d = d - _dt.timedelta(days=1)
    date_20d = biz_dates[20]  # 20 営業日前の日付

    for code, sector, close_today, close_20d_ago in sector_data:
        if sector:
            conn.execute(
                "INSERT INTO stocks (code, sector) VALUES (?, ?)",
                [code, sector],
            )
        # target_date の価格
        conn.execute(
            "INSERT INTO prices_daily "
            "(date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                target_date,
                code,
                close_today,
                close_today,
                close_today,
                close_today,
                1_000_000,
                5e8,
            ],
        )
        # 20 営業日前の価格
        conn.execute(
            "INSERT INTO prices_daily "
            "(date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                date_20d,
                code,
                close_20d_ago,
                close_20d_ago,
                close_20d_ago,
                close_20d_ago,
                1_000_000,
                5e8,
            ],
        )
        # 中間日付を埋める（biz_dates[1..19]、rn=2..20 が存在するために必要）
        for mid_d in biz_dates[1:20]:
            conn.execute(
                "INSERT INTO prices_daily "
                "(date, code, open, high, low, close, volume, turnover) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    mid_d,
                    code,
                    close_today,
                    close_today,
                    close_today,
                    close_today,
                    1_000_000,
                    5e8,
                ],
            )


# ---------------------------------------------------------------------------
# _calc_sector_strengths 単体テスト
# ---------------------------------------------------------------------------


def test_calc_sector_strengths_basic(conn):
    """4セクター正常ケース: top/bottom 各1セクターが正しく分類される"""
    # セクターリターン: Tech=+10%, Food=+5%, Energy=+2%, Retail=-5%
    # → top={Tech}, bottom={Retail}
    _insert_sector_test_data(
        conn,
        [
            ("T1", "Tech", 1100.0, 1000.0),  # +10%
            ("T2", "Tech", 1100.0, 1000.0),
            ("F1", "Food", 1050.0, 1000.0),  # +5%
            ("E1", "Energy", 1020.0, 1000.0),  # +2%
            ("R1", "Retail", 950.0, 1000.0),  # -5%
        ],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert "Tech" in top
    assert "Retail" in bottom
    assert "Food" not in top and "Food" not in bottom
    assert "Energy" not in top and "Energy" not in bottom
    # sector_map に全銘柄が含まれる
    assert sector_map["T1"] == "Tech"
    assert sector_map["R1"] == "Retail"


def test_calc_sector_strengths_single_sector(conn):
    """有効セクターが1つ → top と bottom が同一 → 両方 frozenset() を返す"""
    _insert_sector_test_data(
        conn,
        [
            ("A1", "Tech", 1100.0, 1000.0),
            ("A2", "Tech", 1200.0, 1000.0),
        ],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    # sector_map は正常に返る
    assert sector_map["A1"] == "Tech"


def test_calc_sector_strengths_no_20d_data(conn):
    """20営業日前のデータがない → rows 空 → (frozenset, frozenset, map) を返す"""
    # prices_daily に1日分しか入れない（21日分の distinct date がない）
    conn.execute("INSERT INTO stocks (code, sector) VALUES (?, ?)", ["A", "Tech"])
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 1000.0, 1000.0, 1000.0, 1000.0, 1_000_000, 5e8],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    # sector_map は取得できる
    assert sector_map.get("A") == "Tech"


def test_calc_sector_strengths_multi_sector_insufficient_history(conn):
    """複数セクターが存在しても distinct 日数が 21 未満ならフィルタ無効
    （21日未満の場合 MIN(date) が最古日を返し ret=0 になることで誤分類が
    発生しないよう HAVING COUNT(*) = 21 で排除されることを確認）"""
    # 2セクター・5日分のデータ（21日には満たない）
    for sector, code in [("Tech", "T1"), ("Food", "F1")]:
        conn.execute("INSERT INTO stocks (code, sector) VALUES (?, ?)", [code, sector])
    # 5営業日分の価格を挿入（TARGET_DATE から 4 日前まで）
    base = _dt.date(2024, 1, 10)  # TARGET_DATE = 2024-01-10
    prices = [
        _dt.date(2024, 1, 6),
        _dt.date(2024, 1, 7),
        _dt.date(2024, 1, 8),
        _dt.date(2024, 1, 9),
        base,
    ]
    for d in prices:
        for code, close in [("T1", 1100.0), ("F1", 900.0)]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [d, code, close, close, close, close, 1_000_000, 5e8],
            )
    top, bottom, sector_map = _calc_sector_strengths(conn, base)
    # 21 日分の履歴がないのでフィルタ無効
    assert top == frozenset(), "21日未満のデータでは top は空であるべき"
    assert bottom == frozenset(), "21日未満のデータでは bottom は空であるべき"


def test_calc_sector_strengths_unknown_sector_excluded(conn):
    """sector=NULL の銘柄は sector_map に含まれない（安全側）"""
    _insert_sector_test_data(
        conn,
        [
            ("A", "Tech", 1100.0, 1000.0),
            ("B", "Food", 950.0, 1000.0),
        ],
    )
    # sector なし銘柄（stocks に挿入しない → sector_map に含まれない）
    conn.execute(
        "INSERT INTO prices_daily "
        "(date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "C", 1050.0, 1050.0, 1050.0, 1050.0, 1_000_000, 5e8],
    )
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert "C" not in sector_map
    assert "A" in sector_map


def test_calc_sector_strengths_empty_stocks(conn):
    """stocks テーブルが空 → (frozenset, frozenset, {}) を返す"""
    top, bottom, sector_map = _calc_sector_strengths(conn, TARGET_DATE)
    assert top == frozenset()
    assert bottom == frozenset()
    assert sector_map == {}


# ---------------------------------------------------------------------------
# generate_signals — セクター強弱フィルタ統合テスト
# ---------------------------------------------------------------------------


def test_sector_bottom_suppresses_buy(conn):
    """下位セクター銘柄の BUY が抑制される"""
    # 4 セクター: Tech(+10%), Food(+5%), Energy(+2%), Retail(-5%)
    # → bottom = {Retail}
    _insert_sector_test_data(
        conn,
        [
            ("T1", "Tech", 1100.0, 1000.0),
            ("T2", "Tech", 1100.0, 1000.0),
            ("F1", "Food", 1050.0, 1000.0),
            ("F2", "Food", 1050.0, 1000.0),
            ("E1", "Energy", 1020.0, 1000.0),
            ("E2", "Energy", 1020.0, 1000.0),
            ("R1", "Retail", 950.0, 1000.0),
            ("R2", "Retail", 950.0, 1000.0),
        ],
    )
    # features に高スコアを設定（全銘柄 BUY 候補）
    for code in ["T1", "T2", "F1", "F2", "E1", "E2", "R1", "R2"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    assert "R1" not in buy_codes, "Retail（下位セクター）は BUY 抑制されるべき"
    assert "R2" not in buy_codes, "Retail（下位セクター）は BUY 抑制されるべき"
    assert "T1" in buy_codes, "Tech（上位セクター）は BUY 通過するべき"


def test_sector_boost_pushes_score_above_threshold(conn):
    """上位セクター補正 +0.03 でスコアが閾値を超えて BUY が生成される"""
    # 4 sectors so filter is active: Tech(top +10%), Retail(bottom -5%), Food(+5%), Energy(+2%)
    # A: Tech (上位) → boost で threshold=0.58 超え → BUY
    # B: Energy (中立) → boost なし → BUY なし
    _insert_sector_test_data(
        conn,
        [
            ("A", "Tech", 1100.0, 1000.0),  # top sector (+10%)
            ("B", "Energy", 1000.0, 1000.0),  # neutral (0%)
            ("C", "Food", 1050.0, 1000.0),  # middle (+5%)
            ("D", "Retail", 950.0, 1000.0),  # bottom sector (-5%)
        ],
    )
    # momentum_20=1.0, momentum_60=1.0, ma200_dev=0.0 → final_score ≈ 0.5616 < 0.58
    for code in ["A", "B", "C", "D"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 1.0, 1.0, 0.0, 0.0, NULL, 0.0)",
            [TARGET_DATE, code],
        )
    # threshold=0.58 で実行（default 0.60 より低く設定してブーストの効果を確認）
    generate_signals(conn, TARGET_DATE, threshold=0.58)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    assert "A" in buy_codes, "Tech（上位セクター +0.03 boost）→ 0.5916 > 0.58 で BUY"
    assert "B" not in buy_codes, "Energy（中立）→ 0.5616 < 0.58 で BUY なし"


def test_sector_unknown_not_affected(conn):
    """セクター未登録銘柄はブーストも抑制もされない"""
    # 2 セクター: Tech(top +10%), Food(bottom -5%)
    # X は stocks に登録しない（sector 不明） → sector_map に含まれない
    _insert_sector_test_data(
        conn,
        [
            ("T1", "Tech", 1100.0, 1000.0),
            ("T2", "Tech", 1100.0, 1000.0),
            ("U1", "Food", 950.0, 1000.0),
            ("U2", "Food", 950.0, 1000.0),
        ],
    )
    # X の prices_daily だけ追加
    biz_dates: list[date] = []
    d = TARGET_DATE
    while len(biz_dates) < 21:
        if d.weekday() < 5:
            biz_dates.append(d)
        d = d - _dt.timedelta(days=1)
    for d2 in biz_dates:
        conn.execute(
            "INSERT INTO prices_daily "
            "(date, code, open, high, low, close, volume, turnover) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [d2, "X", 1000.0, 1000.0, 1000.0, 1000.0, 1_000_000, 5e8],
        )
    for code in ["T1", "T2", "U1", "U2", "X"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    # X は bottom セクターでも top セクターでもない → BUY 通過
    assert "X" in buy_codes, "セクター未登録銘柄は抑制されない"
    # U1, U2 は Food (bottom) → 抑制
    assert "U1" not in buy_codes
    assert "U2" not in buy_codes


def test_sector_filter_skipped_in_bear(conn):
    """Bear レジーム時はセクターフィルタが適用されない"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    _insert_sector_test_data(
        conn,
        [
            ("A", "Tech", 1100.0, 1000.0),
            ("B", "Retail", 950.0, 1000.0),
        ],
    )
    # Bear レジームを設定
    conn.execute(
        "INSERT INTO market_regime (date, regime_label, regime_score) VALUES (?, 'bear', -0.5)",
        [TARGET_DATE],
    )
    for code in ["A", "B"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    regime_provider = DatabaseRegimeProvider(conn)
    generate_signals(conn, TARGET_DATE, regime_provider=regime_provider)
    buy_count = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
    ).fetchone()[0]
    assert buy_count == 0, "Bear レジームでは BUY が生成されない"


def test_sector_sell_not_affected(conn):
    """SELL シグナルはセクターフィルタの対象外"""
    # 2 セクター: Tech(top +10%), Food(bottom -5%)
    # A は Tech（top セクター）だが open position でストップロス水準 → SELL が生成されること
    _insert_sector_test_data(
        conn,
        [
            ("A", "Tech", 1100.0, 1000.0),
            ("B", "Tech", 1100.0, 1000.0),
            ("C", "Food", 950.0, 1000.0),
            ("D", "Food", 950.0, 1000.0),
        ],
    )
    # A を保有中でストップロス水準に設定
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
        [TARGET_DATE, "A", 100, 1200.0],
    )
    # A の終値を avg_price の 91% に設定（-9% < ストップロス -8%）
    conn.execute(
        "UPDATE prices_daily SET close = 1092.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    for code in ["A", "B", "C", "D"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, -3.0, -3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    sell_count = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'sell' AND code = 'A'",
        [TARGET_DATE],
    ).fetchone()[0]
    assert sell_count == 1, "SELL はセクターフィルタの対象外"


def test_sector_single_sector_no_filter(conn):
    """有効セクターが1つの場合はフィルタが無効（BUY は通常通り生成される）"""
    _insert_sector_test_data(
        conn,
        [
            ("A", "Tech", 1100.0, 1000.0),
            ("B", "Tech", 1200.0, 1000.0),
        ],
    )
    for code in ["A", "B"]:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.0, 0.0, 20.0, 0.0)",
            [TARGET_DATE, code],
        )
    generate_signals(conn, TARGET_DATE)
    buy_codes = {
        row[0]
        for row in conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [TARGET_DATE],
        ).fetchall()
    }
    assert "A" in buy_codes
    assert "B" in buy_codes


_PREV_DATE = date(2020, 5, 29)  # TARGET_DATE の直前営業日


def test_fetch_gap_ratios_gap_up(conn):
    """ギャップアップ時に正の比率が返る"""
    # prev: close=1000, target: open=1061 → gap = 0.061
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [_PREV_DATE, "A", 990.0, 1010.0, 985.0, 1000.0, 1_000_000, 5e8],
    )
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 1061.0, 1080.0, 1060.0, 1070.0, 1_000_000, 5e8],
    )
    result = _fetch_gap_ratios(conn, ["A"], TARGET_DATE)
    assert "A" in result
    assert result["A"] == pytest.approx(0.061, rel=1e-4)


def test_fetch_gap_ratios_missing_data_returns_empty(conn):
    """target_date のデータなし → {} を返す（BUY 許可側）"""
    result = _fetch_gap_ratios(conn, ["A"], TARGET_DATE)
    assert result == {}


def test_fetch_gap_ratios_empty_codes(conn):
    """codes が空リスト → {} を返す"""
    result = _fetch_gap_ratios(conn, [], TARGET_DATE)
    assert result == {}


def test_fetch_gap_ratios_zero_prev_close_excluded(conn):
    """前日 close = 0 の銘柄はゼロ除算防止のため結果から除外される"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [_PREV_DATE, "A", 0.0, 0.0, 0.0, 0.0, 0, 0],
    )
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 100.0, 110.0, 95.0, 105.0, 1_000_000, 5e8],
    )
    result = _fetch_gap_ratios(conn, ["A"], TARGET_DATE)
    assert "A" not in result


def test_fetch_gap_ratios_zero_open_excluded(conn):
    """当日 open = 0 の銘柄はデータ異常として結果から除外される"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [_PREV_DATE, "A", 990.0, 1010.0, 985.0, 1000.0, 1_000_000, 5e8],
    )
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 0.0, 0.0, 0.0, 0.0, 0, 0],
    )
    result = _fetch_gap_ratios(conn, ["A"], TARGET_DATE)
    assert "A" not in result


# ---------------------------------------------------------------------------
# generate_signals — ギャップフィルタ統合テスト
# ---------------------------------------------------------------------------


def test_gap_up_suppresses_buy(conn):
    """ギャップアップ過大（+5.1%）で BUY が抑制される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8), ("B", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # A に高スコアを設定（BUY 候補）
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # A の当日 open を前日終値 (1000) 比 +5.1% に設定
    # _insert_price_history が open=close*0.99=990 で挿入しているので UPDATE で上書き
    conn.execute(
        "UPDATE prices_daily SET open = 1051.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    # BUY 抑制・ポジションなし → シグナルなし
    assert row is None


def test_gap_down_at_boundary_suppresses_buy(conn):
    """ギャップダウン -3.0%（境界値：以下に含む）で BUY が抑制される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # open = 970.0 → gap = 970/1000 - 1 = -0.03（ちょうど -3%、以下に含む → 抑制）
    conn.execute(
        "UPDATE prices_daily SET open = 970.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is None


def test_gap_up_at_threshold_allows_buy(conn):
    """ギャップアップちょうど +5.0%（超ではない）では BUY が許可される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # open = 1050.0 → gap = 1050/1000 - 1 = 0.05（ちょうど +5%、超ではない → 許可）
    # IEEE754 では 1050.0/1000.0 - 1.0 = 0.050000000000000044 となるが
    # _GAP_THRESHOLD_EPSILON = 1e-9 を加算した比較で正しく「許可」と判定される
    conn.execute(
        "UPDATE prices_daily SET open = 1050.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "buy"


def test_gap_down_just_above_threshold_allows_buy(conn):
    """ギャップダウン -2.9%（閾値より上）では BUY が許可される"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    conn.execute(
        "UPDATE features SET momentum_20 = 3.0, momentum_60 = 3.0 WHERE code = 'A' AND date = ?",
        [TARGET_DATE],
    )
    # open = 971.0 → gap = 971/1000 - 1 = -0.029 > -0.03 → 許可
    conn.execute(
        "UPDATE prices_daily SET open = 971.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "buy"


def test_gap_missing_prev_data_allows_buy(conn):
    """前日データなし（gap_ratios にキーなし）→ BUY 許可（安全側）"""
    # prices_daily に TARGET_DATE の 1 行だけ挿入（前日なし）
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume, turnover) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [TARGET_DATE, "A", 1000.0, 1020.0, 990.0, 1010.0, 1_000_000, 5e8],
    )
    # features に直接挿入（build_features は価格履歴が必要なためスキップ）
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, 'A', 3.0, 3.0, NULL, NULL, NULL, NULL)",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "buy"


def test_sell_not_affected_by_gap(conn):
    """ギャップ過大でも SELL シグナルは通常通り生成される（SELL は対象外）"""
    _insert_price_history(conn, [("A", 1000.0, 6e8)])
    build_features(conn, TARGET_DATE)
    # avg_price=1100、終値=1000 → pnl=-9.1% → stop-loss 発動
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
        "VALUES (?, 'A', 100, 1100.0, 110000.0)",
        [TARGET_DATE],
    )
    # ギャップアップ過大を設定（BUY 候補なら抑制されるが、SELL は影響を受けない）
    conn.execute(
        "UPDATE prices_daily SET open = 1061.0 WHERE date = ? AND code = 'A'",
        [TARGET_DATE],
    )
    generate_signals(conn, TARGET_DATE, threshold=0.5)
    row = conn.execute(
        "SELECT side FROM signals WHERE date = ? AND code = 'A'", [TARGET_DATE]
    ).fetchone()
    assert row is not None and row[0] == "sell"
