"""バックテストフレームワーク テスト"""
from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """インメモリ DuckDB 接続（テスト毎に新規作成）。"""
    c = init_schema(":memory:")
    yield c
    c.close()


def _make_history(values: list[float]) -> list:
    """portfolio_value のリストから DailySnapshot のリストを生成する。"""
    from kabusys.backtest.simulator import DailySnapshot
    base = date(2024, 1, 1)
    return [
        DailySnapshot(
            date=base + timedelta(days=i),
            cash=0.0,
            positions={},
            portfolio_value=v,
        )
        for i, v in enumerate(values)
    ]


def _make_trades(pnl_list: list[float]) -> list:
    """realized_pnl のリストから TradeRecord のリストを生成する（SELL のみ）。"""
    from kabusys.backtest.simulator import TradeRecord
    base = date(2024, 1, 2)
    return [
        TradeRecord(
            date=base + timedelta(days=i),
            code="1234",
            side="sell",
            shares=100,
            price=1000.0,
            commission=55.0,
            realized_pnl=pnl,
        )
        for i, pnl in enumerate(pnl_list)
    ]


# ---------------------------------------------------------------------------
# Task 2: metrics.py
# ---------------------------------------------------------------------------

def test_metrics_cagr_one_year():
    """1年で資産が2倍 → CAGR = 100%。"""
    from kabusys.backtest.metrics import calc_metrics
    # 365 日で 1_000_000 → 2_000_000
    history = _make_history([1_000_000] + [1_000_000] * 364 + [2_000_000])
    result = calc_metrics(history, [])
    assert abs(result.cagr - 1.0) < 0.01  # ≈ 100%


def test_metrics_max_drawdown():
    """100 → 80 → 90 の推移 → MDD = 0.20。"""
    from kabusys.backtest.metrics import calc_metrics
    history = _make_history([100.0, 80.0, 90.0])
    result = calc_metrics(history, [])
    assert abs(result.max_drawdown - 0.20) < 1e-9


def test_metrics_sharpe_constant_return():
    """毎日同一リターン → 標準偏差 0 → Sharpe = 0.0（ゼロ除算回避）。"""
    from kabusys.backtest.metrics import calc_metrics
    history = _make_history([1_000_000 + i * 1000 for i in range(252)])
    result = calc_metrics(history, [])
    assert math.isfinite(result.sharpe_ratio)


def test_metrics_win_rate():
    """勝ち2件・負け1件 → win_rate ≈ 0.667。"""
    from kabusys.backtest.metrics import calc_metrics
    trades = _make_trades([10000.0, 5000.0, -3000.0])
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), trades)
    assert abs(result.win_rate - 2 / 3) < 1e-9


def test_metrics_payoff_ratio():
    """平均利益 7500、平均損失 3000 → payoff ≈ 2.5。"""
    from kabusys.backtest.metrics import calc_metrics
    trades = _make_trades([10000.0, 5000.0, -3000.0])
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), trades)
    assert abs(result.payoff_ratio - 2.5) < 1e-9


def test_metrics_no_trades():
    """トレードなし → win_rate=0.0, payoff_ratio=0.0, total_trades=0。"""
    from kabusys.backtest.metrics import calc_metrics
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), [])
    assert result.win_rate == 0.0
    assert result.payoff_ratio == 0.0
    assert result.total_trades == 0


# ---------------------------------------------------------------------------
# Task 3: simulator.py
# ---------------------------------------------------------------------------

def _make_simulator(initial_cash: float = 1_000_000):
    from kabusys.backtest.simulator import PortfolioSimulator
    return PortfolioSimulator(initial_cash=initial_cash)


def test_simulator_buy_reduces_cash():
    """BUY 約定 → 現金が (株数 × 約定価格 + 手数料) 分減る。"""
    sim = _make_simulator(1_000_000)
    signals = [{"code": "1234", "side": "buy", "shares": 100}]
    open_prices = {"1234": 1000.0}
    slippage = 0.001
    commission = 0.00055

    sim.execute_orders(signals, open_prices, slippage, commission)

    entry_price = 1000.0 * (1 + slippage)  # 1001.0
    shares = 100
    cost = shares * entry_price
    comm = cost * commission
    expected_cash = 1_000_000 - cost - comm
    assert abs(sim.cash - expected_cash) < 0.01


def test_simulator_buy_slippage():
    """BUY 約定価格 = open * (1 + slippage_rate)。"""
    sim = _make_simulator()
    signals = [{"code": "1234", "side": "buy", "shares": 100}]
    open_prices = {"1234": 2000.0}
    sim.execute_orders(signals, open_prices, slippage_rate=0.001, commission_rate=0.00055)

    assert len(sim.trades) == 1
    trade = sim.trades[0]
    assert abs(trade.price - 2000.0 * 1.001) < 1e-6


def test_simulator_sell_realized_pnl():
    """SELL → realized_pnl = shares * (exit_price - cost_basis) - commission。"""
    sim = _make_simulator()
    # まず BUY して cost_basis を確立
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "shares": 300}],
        {"1234": 1000.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    buy_trade = sim.trades[0]
    shares = buy_trade.shares

    # SELL
    sim.execute_orders(
        [{"code": "1234", "side": "sell"}],
        {"1234": 1200.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    sell_trade = sim.trades[1]
    expected_pnl = shares * (1200.0 - 1000.0)
    assert abs(sell_trade.realized_pnl - expected_pnl) < 0.01


def test_simulator_sell_slippage():
    """SELL 約定価格 = open * (1 - slippage_rate)。"""
    sim = _make_simulator()
    # 強制的に保有状態を作る
    sim.positions["1234"] = 100
    sim.cost_basis["1234"] = 900.0
    sim.cash -= 90_000

    sim.execute_orders(
        [{"code": "1234", "side": "sell"}],
        {"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.0,
    )
    assert abs(sim.trades[0].price - 999.0) < 1e-6


def test_simulator_mark_to_market():
    """mark_to_market → portfolio_value = cash + sum(shares * close)。"""
    from kabusys.backtest.simulator import PortfolioSimulator
    sim = PortfolioSimulator(initial_cash=500_000)
    sim.positions = {"1234": 100, "5678": 200}
    sim.cost_basis = {"1234": 900.0, "5678": 500.0}
    sim.cash = 200_000

    close_prices = {"1234": 1000.0, "5678": 600.0}
    sim.mark_to_market(date(2024, 1, 5), close_prices)

    expected_pv = 200_000 + 100 * 1000.0 + 200 * 600.0
    assert len(sim.history) == 1
    assert abs(sim.history[0].portfolio_value - expected_pv) < 0.01


def test_simulator_no_price_skips_buy():
    """open_prices に code が存在しない BUY シグナルはスキップ（ログのみ）。"""
    sim = _make_simulator()
    sim.execute_orders(
        [{"code": "9999", "side": "buy", "shares": 100}],
        {},  # 価格なし
        slippage_rate=0.001,
        commission_rate=0.00055,
    )
    assert sim.cash == 1_000_000  # 変化なし
    assert len(sim.trades) == 0


def test_simulator_insufficient_cash_skips_buy():
    """shares > 0 でも現金不足なら全体をスキップ。"""
    sim = _make_simulator(initial_cash=100)  # 現金が極端に少ない
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "shares": 100}],
        {"1234": 10_000.0},  # 100株 × 10000円 = 1,000,000 円必要
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    assert len(sim.trades) == 0  # 現金不足でスキップ


# ---------------------------------------------------------------------------
# Task 4: engine.py ヘルパー
# ---------------------------------------------------------------------------

def _insert_price(conn, code: str, d, open_: float, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, open_, close, open_, close, 1_000_000],
    )


def _insert_calendar(conn, d, is_trading: bool = True) -> None:
    conn.execute(
        "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, ?)",
        [d, is_trading],
    )


def test_build_backtest_conn_copies_prices(conn):
    """_build_backtest_conn → prices_daily が bt_conn にコピーされる。"""
    from kabusys.backtest.engine import _build_backtest_conn
    from datetime import date

    d = date(2024, 1, 5)
    _insert_price(conn, "1234", d, open_=1000.0, close=1010.0)

    bt_conn = _build_backtest_conn(conn, date(2024, 1, 5), date(2024, 1, 5))
    row = bt_conn.execute(
        "SELECT close FROM prices_daily WHERE code = ? AND date = ?", ["1234", d]
    ).fetchone()
    assert row is not None
    assert abs(float(row[0]) - 1010.0) < 1e-6
    bt_conn.close()


def test_fetch_open_and_close_prices(conn):
    """_fetch_open_prices / _fetch_close_prices → 始値・終値を辞書で返す。"""
    from kabusys.backtest.engine import _fetch_open_prices, _fetch_close_prices
    from datetime import date

    d = date(2024, 1, 8)
    _insert_price(conn, "1234", d, open_=980.0, close=1020.0)
    _insert_price(conn, "5678", d, open_=500.0, close=510.0)

    opens = _fetch_open_prices(conn, d)
    closes = _fetch_close_prices(conn, d)

    assert abs(opens["1234"] - 980.0) < 1e-6
    assert abs(closes["1234"] - 1020.0) < 1e-6
    assert abs(opens["5678"] - 500.0) < 1e-6


def test_write_positions_idempotent(conn):
    """_write_positions → 同日に2回呼んでも1行のみ残る。"""
    from kabusys.backtest.engine import _write_positions
    from datetime import date

    d = date(2024, 1, 10)
    _write_positions(conn, d, {"1234": 100}, {"1234": 950.0})
    _write_positions(conn, d, {"1234": 100}, {"1234": 950.0})

    count = conn.execute(
        "SELECT COUNT(*) FROM positions WHERE date = ?", [d]
    ).fetchone()[0]
    assert count == 1


def test_write_positions_values(conn):
    """_write_positions → position_size と avg_price が正しく書き込まれる。"""
    from kabusys.backtest.engine import _write_positions
    from datetime import date

    d = date(2024, 1, 11)
    _write_positions(conn, d, {"1234": 200, "5678": 50}, {"1234": 1050.0, "5678": 600.0})

    rows = {
        row[0]: (row[1], float(row[2]))
        for row in conn.execute(
            "SELECT code, position_size, avg_price FROM positions WHERE date = ?", [d]
        ).fetchall()
    }
    assert rows["1234"] == (200, 1050.0)
    assert rows["5678"] == (50, 600.0)


# ---------------------------------------------------------------------------
# Task 5: run_backtest 統合テスト
# ---------------------------------------------------------------------------

def _setup_minimal_backtest(conn):
    """3営業日分の最小限データをセットアップするヘルパー。"""
    from datetime import date

    days = [date(2024, 1, 4), date(2024, 1, 5), date(2024, 1, 9)]
    for d in days:
        _insert_calendar(conn, d, is_trading=True)
        _insert_price(conn, "1234", d, open_=1000.0, close=1050.0)
        conn.execute(
            """INSERT INTO features
               (date, code, momentum_20, momentum_60, volatility_20,
                volume_ratio, per, ma200_dev)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [d, "1234", 1.5, 1.2, -0.5, 1.3, 0.5, 0.05],
        )
    return days


def test_run_backtest_returns_result(conn):
    """run_backtest が BacktestResult を返す（最低限の動作確認）。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
    )

    assert isinstance(result, BacktestResult)
    assert len(result.history) >= 1
    assert result.metrics is not None


def test_run_backtest_cash_decreases_on_buy(conn):
    """BUY 約定後に現金が減少している。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)
    initial_cash = 10_000_000

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        initial_cash=initial_cash,
    )

    # 何かトレードがあれば現金が変わっているはず
    if result.trades:
        buys = [t for t in result.trades if t.side == "buy"]
        if buys:
            final_cash = result.history[-1].cash
            assert final_cash < initial_cash


def test_run_backtest_no_lookahead(conn):
    """end_date より後の価格データは結果に影響しない（Look-ahead 防止）。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)

    # 未来の価格（end_date + 1日）を挿入
    future_date = date(2024, 1, 10)
    _insert_price(conn, "1234", future_date, open_=9999.0, close=9999.0)
    conn.execute(
        """INSERT INTO features
           (date, code, momentum_20, momentum_60, volatility_20,
            volume_ratio, per, ma200_dev)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [future_date, "1234", 99.0, 99.0, -99.0, 99.0, 0.01, 99.0],
    )

    result1 = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
    )

    # end_date 以降のスナップショットが存在しないこと
    for snap in result1.history:
        assert snap.date <= date(2024, 1, 9), f"未来日付 {snap.date} が履歴に含まれている"


def test_run_backtest_idempotent(conn):
    """同一パラメータで2回実行しても metrics が同一値になる。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)

    result1 = run_backtest(conn=conn, start_date=date(2024, 1, 4), end_date=date(2024, 1, 9))
    result2 = run_backtest(conn=conn, start_date=date(2024, 1, 4), end_date=date(2024, 1, 9))

    assert abs(result1.metrics.cagr - result2.metrics.cagr) < 1e-9
    assert len(result1.history) == len(result2.history)


def test_run_backtest_max_position_pct(conn):
    """max_position_pct=0.10 → 1銘柄への投資が portfolio_value の 10% 超にならない。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)
    initial_cash = 10_000_000

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        initial_cash=initial_cash,
        max_position_pct=0.10,
    )

    for trade in result.trades:
        if trade.side == "buy":
            invested = trade.shares * trade.price
            assert invested <= initial_cash * 0.10 * 1.01  # 1% の誤差許容


# ---------------------------------------------------------------------------
# Task 6: engine.py — Phase 5 helpers and run_backtest updates
# ---------------------------------------------------------------------------

def test_fetch_regime_returns_bull_on_no_data(conn):
    """_fetch_regime: market_regime にデータなし → 'bull' を返す。"""
    from kabusys.backtest.engine import _fetch_regime
    from datetime import date

    result = _fetch_regime(conn, date(2024, 1, 5))
    assert result == "bull"


def test_fetch_regime_returns_correct_label(conn):
    """_fetch_regime: market_regime にデータあり → regime_label を返す。"""
    from kabusys.backtest.engine import _fetch_regime
    from datetime import date

    d = date(2024, 1, 5)
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, -0.5, "bear"],
    )
    result = _fetch_regime(conn, d)
    assert result == "bear"


def test_fetch_sector_map_empty_table(conn):
    """_fetch_sector_map: stocks テーブルが空なら {}。"""
    from kabusys.backtest.engine import _fetch_sector_map

    result = _fetch_sector_map(conn)
    assert result == {}


def test_fetch_sector_map_returns_data(conn):
    """_fetch_sector_map: stocks テーブルからセクターマップを返す。"""
    from kabusys.backtest.engine import _fetch_sector_map

    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト", "Prime", "電気機器"],
    )
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["5678", "サンプル", "Standard", "機械"],
    )
    result = _fetch_sector_map(conn)
    assert result == {"1234": "電気機器", "5678": "機械"}


def test_build_backtest_conn_copies_stocks(conn):
    """_build_backtest_conn → stocks テーブルが bt_conn にコピーされる。"""
    from kabusys.backtest.engine import _build_backtest_conn
    from datetime import date

    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1234", "テスト", "Prime", "電気機器"],
    )
    bt_conn = _build_backtest_conn(conn, date(2024, 1, 5), date(2024, 1, 5))
    row = bt_conn.execute("SELECT sector FROM stocks WHERE code = '1234'").fetchone()
    assert row is not None
    assert row[0] == "電気機器"
    bt_conn.close()


def test_read_day_signals_includes_score(conn):
    """_read_day_signals → buy_signals に score フィールドが含まれる。"""
    from kabusys.backtest.engine import _read_day_signals
    from datetime import date

    d = date(2024, 1, 5)
    conn.execute(
        "INSERT INTO signals (date, code, side, score, signal_rank) VALUES (?, ?, ?, ?, ?)",
        [d, "1234", "buy", 0.85, 1],
    )
    buy_signals, sell_signals = _read_day_signals(conn, d)
    assert len(buy_signals) == 1
    assert "score" in buy_signals[0]
    assert abs(buy_signals[0]["score"] - 0.85) < 1e-9


def test_run_backtest_new_params_accepted(conn):
    """run_backtest が新パラメータ（allocation_method, max_positions 等）を受け付ける。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        allocation_method="equal",
        max_positions=5,
        max_utilization=0.70,
    )

    assert isinstance(result, BacktestResult)


def test_run_backtest_risk_based_method(conn):
    """run_backtest の allocation_method="risk_based" が動作する。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        allocation_method="risk_based",
        risk_pct=0.005,
        stop_loss_pct=0.08,
    )

    assert isinstance(result, BacktestResult)


def test_run_backtest_default_max_position_pct_is_010(conn):
    """run_backtest のデフォルト max_position_pct は 0.10（Phase 5 設計書準拠）。"""
    import inspect
    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    default = sig.parameters["max_position_pct"].default
    assert default == 0.10, f"max_position_pct のデフォルトが {default}（0.10 であること）"


# ---------------------------------------------------------------------------
# レビュー対応: 追加テスト
# ---------------------------------------------------------------------------

def test_fetch_sector_map_excludes_empty_string_sector(conn):
    """_fetch_sector_map: 空文字セクターは除外される（'unknown' フォールバックに委ねる）。"""
    from kabusys.backtest.engine import _fetch_sector_map

    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["1111", "正常", "Prime", "電気機器"],
    )
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["2222", "空文字セクター", "Prime", ""],
    )
    conn.execute(
        "INSERT INTO stocks (code, name, market, sector) VALUES (?, ?, ?, ?)",
        ["3333", "スペースのみ", "Prime", "   "],
    )

    result = _fetch_sector_map(conn)

    assert "1111" in result
    assert result["1111"] == "電気機器"
    assert "2222" not in result, "空文字セクターはマップに含まれてはならない"
    assert "3333" not in result, "スペースのみのセクターはマップに含まれてはならない"


def test_execute_buy_partial_fill_when_insufficient_cash():
    """_execute_buy: 現金不足でも max_affordable_shares で部分約定する。

    cash=95_000, entry_price=1000*(1+0.001)=1001, commission_rate=0.00055
    total_cost(100株) = 100*1001*(1+0.00055) = 101_155.5 > 95_000
    → max_affordable = floor(95_000 / (1001 * 1.00055)) = floor(94.86) = 94 株
    → 94 株で約定
    """
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=95_000.0)
    sim._execute_buy(
        code="1234",
        shares=100,
        open_prices={"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.00055,
        trading_day=date(2024, 1, 5),
    )

    assert "1234" in sim.positions, "部分約定で保有が発生するはず"
    assert sim.positions["1234"] > 0
    assert sim.positions["1234"] < 100, "100株未満の部分約定"
    assert sim.cash >= 0, "現金がマイナスになってはならない"


def test_execute_buy_full_skip_when_price_too_high():
    """_execute_buy: 1株も買えない場合は約定しない。"""
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=500.0)  # 1株1000円を買えない
    sim._execute_buy(
        code="1234",
        shares=100,
        open_prices={"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.00055,
        trading_day=date(2024, 1, 5),
    )

    assert "1234" not in sim.positions
    assert sim.cash == 500.0


def test_run_backtest_invalid_allocation_method_raises(conn):
    """run_backtest に不正な allocation_method を渡すと ValueError が発生する。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date
    import pytest

    _setup_minimal_backtest(conn)

    with pytest.raises(ValueError, match="allocation_method"):
        run_backtest(
            conn=conn,
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 9),
            allocation_method="invalid_method",
        )


def test_run_backtest_available_cash_capped_by_max_utilization(conn):
    """available_cash = min(cash*multiplier, pv*max_utilization) が適用される。

    max_utilization=0.0 なら available_cash=0 → 発注株数がゼロになる。
    """
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        initial_cash=10_000_000,
        max_utilization=0.0,  # 全ポジション禁止
    )

    buy_trades = [t for t in result.trades if t.side == "buy"]
    assert len(buy_trades) == 0, "max_utilization=0.0 では BUY 約定が発生してはならない"


def test_execute_buy_partial_fill_lot_size_rounded(conn):
    """_execute_buy: 部分約定は lot_size=100 で単元丸めされる。

    cash=150_000, entry_price≈1001, lot_size=100
    → max_affordable_raw = floor(150_000 / 1001) = 149
    → lot 丸め: (149 // 100) * 100 = 100 株で約定
    """
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=150_000.0)
    sim._execute_buy(
        code="1234",
        shares=200,
        open_prices={"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.00055,
        trading_day=date(2024, 1, 5),
        lot_size=100,
    )

    assert "1234" in sim.positions
    assert sim.positions["1234"] % 100 == 0, "部分約定でも単元株単位になること"
    assert sim.cash >= 0


def test_execute_buy_partial_fill_lot_size_default_no_rounding():
    """lot_size=1（デフォルト）では単元丸めせずに部分約定する（後方互換）。"""
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=95_000.0)
    sim._execute_buy(
        code="1234",
        shares=100,
        open_prices={"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.00055,
        trading_day=date(2024, 1, 5),
        lot_size=1,  # デフォルト: 単元丸めなし
    )

    assert "1234" in sim.positions
    assert sim.positions["1234"] < 100


def test_select_candidates_tiebreak_by_signal_rank():
    """同一スコアの銘柄は signal_rank 昇順でタイブレークされる。"""
    from kabusys.portfolio.portfolio_builder import select_candidates

    signals = [
        {"code": "A", "signal_rank": 3, "score": 0.5},
        {"code": "B", "signal_rank": 1, "score": 0.5},  # 同スコア・より低い rank
        {"code": "C", "signal_rank": 2, "score": 0.5},
    ]
    result = select_candidates(signals, max_positions=2)
    codes = [c["code"] for c in result]
    assert codes[0] == "B", "signal_rank が最小（優先度が高い）の B が先頭"
    assert codes[1] == "C"


def test_execute_buy_non_lot_multiple_warns(caplog):
    """_execute_buy: shares が lot_size の倍数でない場合に WARNING ログを出す。"""
    import logging
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=1_000_000.0)
    with caplog.at_level(logging.WARNING, logger="kabusys.backtest.simulator"):
        sim._execute_buy(
            code="1234",
            shares=150,  # lot_size=100 の倍数でない
            open_prices={"1234": 1000.0},
            slippage_rate=0.001,
            commission_rate=0.00055,
            trading_day=date(2024, 1, 5),
            lot_size=100,
        )
    assert any("単元株数" in r.message for r in caplog.records), "WARNING ログが出ること"


def test_execute_buy_lot_multiple_no_warn(caplog):
    """_execute_buy: shares が lot_size の倍数のとき WARNING ログは出ない。"""
    import logging
    from kabusys.backtest.simulator import PortfolioSimulator
    from datetime import date

    sim = PortfolioSimulator(initial_cash=1_000_000.0)
    with caplog.at_level(logging.WARNING, logger="kabusys.backtest.simulator"):
        sim._execute_buy(
            code="1234",
            shares=200,  # 100 の倍数
            open_prices={"1234": 1000.0},
            slippage_rate=0.001,
            commission_rate=0.00055,
            trading_day=date(2024, 1, 5),
            lot_size=100,
        )
    assert not any("単元株数" in r.message for r in caplog.records), "WARNING ログが出ないこと"


def test_run_backtest_invalid_risk_pct_raises(conn):
    """risk_pct が範囲外なら ValueError を発生させる（risk_based 時のみ）。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date
    import pytest

    _setup_minimal_backtest(conn)

    with pytest.raises(ValueError, match="risk_pct"):
        run_backtest(
            conn=conn,
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 9),
            allocation_method="risk_based",
            risk_pct=0.0,
        )


def test_run_backtest_invalid_stop_loss_pct_raises(conn):
    """stop_loss_pct=0 は除算ゼロになるため ValueError を発生させる。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date
    import pytest

    _setup_minimal_backtest(conn)

    with pytest.raises(ValueError, match="stop_loss_pct"):
        run_backtest(
            conn=conn,
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 9),
            stop_loss_pct=0.0,
        )


def test_run_backtest_invalid_max_utilization_raises(conn):
    """max_utilization が範囲外なら ValueError を発生させる。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date
    import pytest

    _setup_minimal_backtest(conn)

    with pytest.raises(ValueError, match="max_utilization"):
        run_backtest(
            conn=conn,
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 9),
            max_utilization=1.5,
        )


def test_run_backtest_cli_params(conn):
    """run_backtest が CLI から渡される新パラメータを正しく受け付ける。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        allocation_method="equal",
        max_utilization=0.50,
        max_positions=5,
        risk_pct=0.01,
        stop_loss_pct=0.10,
    )

    assert isinstance(result, BacktestResult)
