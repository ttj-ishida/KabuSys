"""tests/test_dashboard_pages.py — dashboard_data.py のデータロード関数テスト"""

from __future__ import annotations

import sqlite3

import duckdb
import pytest

from kabusys.monitoring.monitoring_db import init_monitoring_db


@pytest.fixture
def duck_conn():
    """スキーマ付きのインメモリ DuckDB コネクション。"""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signal_queue (
            signal_id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            size BIGINT NOT NULL,
            order_type VARCHAR NOT NULL,
            price DECIMAL(18,4),
            status VARCHAR NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            processed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE signals (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            score DOUBLE,
            signal_rank INTEGER,
            size_multiplier DOUBLE NOT NULL DEFAULT 1.0,
            PRIMARY KEY (date, code, side)
        )
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            target_weight DOUBLE,
            target_size BIGINT,
            PRIMARY KEY (date, code)
        )
    """)
    conn.execute("""
        CREATE TABLE portfolio_performance (
            date DATE NOT NULL,
            env VARCHAR NOT NULL DEFAULT 'live',
            equity DECIMAL(20,4) NOT NULL,
            cash DECIMAL(20,4) NOT NULL DEFAULT 0,
            drawdown DOUBLE,
            daily_return DOUBLE,
            PRIMARY KEY (date, env)
        )
    """)
    conn.execute("""
        CREATE TABLE positions (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            position_size BIGINT NOT NULL,
            avg_price DECIMAL(18,4) NOT NULL,
            market_value DECIMAL(20,4),
            PRIMARY KEY (date, code)
        )
    """)
    conn.execute("""
        CREATE TABLE trades (
            trade_id VARCHAR PRIMARY KEY,
            order_id VARCHAR NOT NULL,
            datetime TIMESTAMP NOT NULL,
            code VARCHAR NOT NULL,
            price DECIMAL(18,4) NOT NULL,
            size BIGINT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE market_regime (
            date DATE PRIMARY KEY,
            regime_score DOUBLE NOT NULL,
            regime_label VARCHAR NOT NULL,
            ma200_ratio DOUBLE,
            macro_sentiment DOUBLE,
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        )
    """)
    conn.execute("""
        CREATE TABLE ai_scores (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            sentiment_score DOUBLE,
            regime_score DOUBLE,
            ai_score DOUBLE,
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (date, code)
        )
    """)
    return conn


@pytest.fixture
def mon_conn():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    return conn


# ---------------------------------------------------------------------------
# Home ページ — load_error_logs（SQLite）
# ---------------------------------------------------------------------------


def test_load_error_logs_empty(mon_conn):
    from kabusys.monitoring.dashboard_data import load_error_logs

    result = load_error_logs(mon_conn)
    assert result == []


def test_load_error_logs_returns_only_error_events(mon_conn):
    from kabusys.monitoring.dashboard_data import load_error_logs
    from kabusys.monitoring.monitoring_db import MonitoringDB

    db = MonitoringDB(mon_conn)
    db.log_risk_event(
        "ORDER_ERROR", "order_fail_count", 1.0, 0.0, detail="注文エラー発生"
    )
    db.log_risk_event(
        "POSITION_UPDATE", "pos_update", 0.0, 0.0, detail="通常イベント"
    )  # 除外されるはず

    result = load_error_logs(mon_conn)
    assert len(result) == 1
    assert result[0]["event_type"] == "ORDER_ERROR"


# ---------------------------------------------------------------------------
# Signal Queue ページ（DuckDB）
# ---------------------------------------------------------------------------


def test_load_signal_queue_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_signal_queue

    df = load_signal_queue(duck_conn)
    assert df.empty


def test_load_signal_queue_returns_rows(duck_conn):
    from kabusys.monitoring.dashboard_data import load_signal_queue

    duck_conn.execute("""
        INSERT INTO signal_queue (signal_id, date, code, side, size, order_type, status)
        VALUES ('sq-1', '2024-09-01', '7203', 'buy', 100, 'market', 'pending')
    """)
    df = load_signal_queue(duck_conn)
    assert len(df) == 1
    assert df.iloc[0]["code"] == "7203"


def test_load_portfolio_targets_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_portfolio_targets

    df = load_portfolio_targets(duck_conn)
    assert df.empty


def test_load_portfolio_targets_latest_date_only(duck_conn):
    from kabusys.monitoring.dashboard_data import load_portfolio_targets

    duck_conn.execute("""
        INSERT INTO portfolio_targets (date, code, target_weight, target_size)
        VALUES ('2024-09-01', '7203', 0.05, 100),
               ('2024-09-02', '6758', 0.10, 50)
    """)
    df = load_portfolio_targets(duck_conn)
    assert len(df) == 1
    assert str(df.iloc[0]["date"])[:10] == "2024-09-02"


def test_load_signals_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_signals

    df = load_signals(duck_conn)
    assert df.empty


# ---------------------------------------------------------------------------
# Performance ページ（DuckDB）
# ---------------------------------------------------------------------------


def test_load_portfolio_performance_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_portfolio_performance

    df = load_portfolio_performance(duck_conn, env="live", days=90)
    assert df.empty


def test_load_portfolio_performance_returns_rows(duck_conn):
    from kabusys.monitoring.dashboard_data import load_portfolio_performance

    duck_conn.execute("""
        INSERT INTO portfolio_performance (date, env, equity, cash, drawdown, daily_return)
        VALUES (current_date, 'live', 10000000, 2000000, -0.02, 0.005)
    """)
    df = load_portfolio_performance(duck_conn, env="live", days=90)
    assert len(df) == 1
    assert float(df.iloc[0]["equity"]) == pytest.approx(10000000.0)


def test_load_portfolio_performance_filters_env(duck_conn):
    from kabusys.monitoring.dashboard_data import load_portfolio_performance

    duck_conn.execute("""
        INSERT INTO portfolio_performance (date, env, equity, cash)
        VALUES (current_date, 'live',  10000000, 2000000),
               (current_date, 'paper',  5000000, 1000000)
    """)
    df = load_portfolio_performance(duck_conn, env="live", days=90)
    assert len(df) == 1
    assert df.iloc[0]["env"] == "live"


def test_load_open_positions_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_open_positions

    df = load_open_positions(duck_conn)
    assert df.empty


def test_load_open_positions_excludes_zero_size(duck_conn):
    from kabusys.monitoring.dashboard_data import load_open_positions

    duck_conn.execute("""
        INSERT INTO positions (date, code, position_size, avg_price, market_value)
        VALUES (current_date, '7203', 100, 2500.0, 250000.0),
               (current_date, '6758', 0,   5000.0,      0.0)
    """)
    df = load_open_positions(duck_conn)
    assert len(df) == 1
    assert df.iloc[0]["code"] == "7203"


def test_load_recent_trades_empty(duck_conn):
    from kabusys.monitoring.dashboard_data import load_recent_trades

    df = load_recent_trades(duck_conn)
    assert df.empty


# ---------------------------------------------------------------------------
# Strategy Lab ページ（DuckDB）
# ---------------------------------------------------------------------------


def test_load_market_regime_empty(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_market_regime

    df = load_market_regime(duck_conn, days=30)
    assert df.empty


def test_load_market_regime_returns_rows(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_market_regime

    duck_conn.execute("""
        INSERT INTO market_regime (date, regime_score, regime_label)
        VALUES (current_date, 0.65, 'bull')
    """)
    df = load_market_regime(duck_conn, days=30)
    assert len(df) == 1
    assert df.iloc[0]["regime_label"] == "bull"


def test_load_ai_scores_empty(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_ai_scores

    df = load_ai_scores(duck_conn)
    assert df.empty


def test_load_ai_scores_returns_latest_date_only(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_ai_scores

    duck_conn.execute("""
        INSERT INTO ai_scores (date, code, ai_score)
        VALUES ('2024-09-01', '7203', 0.8),
               ('2024-09-02', '6758', 0.9)
    """)
    df = load_ai_scores(duck_conn)
    assert len(df) == 1
    assert df.iloc[0]["code"] == "6758"


def test_load_signal_summary_empty(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_signal_summary

    df = load_signal_summary(duck_conn, days=30)
    assert df.empty


def test_load_signal_summary_counts_by_side(duck_conn):
    from kabusys.monitoring.strategy_lab_data import load_signal_summary

    duck_conn.execute("""
        INSERT INTO signals (date, code, side, score, signal_rank)
        VALUES (current_date, '7203', 'buy',  0.8, 1),
               (current_date, '6758', 'buy',  0.6, 2),
               (current_date, '9984', 'sell', 0.3, 3)
    """)
    df = load_signal_summary(duck_conn, days=30)
    assert len(df) == 1
    assert int(df.iloc[0]["buy_count"]) == 2
    assert int(df.iloc[0]["sell_count"]) == 1
