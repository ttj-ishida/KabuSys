"""tests/test_strategy_lab_data.py — strategy_lab_data.py のデータロード関数テスト"""

import duckdb
import pytest


@pytest.fixture
def duck_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE market_regime (
            date DATE, regime_score DOUBLE, regime_label VARCHAR,
            ma200_ratio DOUBLE, macro_sentiment DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE ai_scores (
            date DATE, code VARCHAR, sentiment_score DOUBLE,
            regime_score DOUBLE, ai_score DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE signals (
            date DATE, code VARCHAR, side VARCHAR,
            score DOUBLE, signal_rank INTEGER, size_multiplier DOUBLE
        )
    """)
    yield conn
    conn.close()


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
