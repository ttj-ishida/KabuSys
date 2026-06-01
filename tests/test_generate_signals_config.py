"""
Tests that generate_signals() resolves None sentinels from strategy_config.yaml.
"""

import textwrap
from datetime import date
from unittest.mock import patch

import duckdb


def _make_db():
    """Create minimal in-memory DuckDB with required tables."""
    conn = duckdb.connect()
    conn.execute("""
        CREATE TABLE features (
            date DATE, code VARCHAR, momentum_20 DOUBLE, momentum_60 DOUBLE,
            volatility_20 DOUBLE, volume_ratio DOUBLE, per DOUBLE, pbr DOUBLE,
            div_yield DOUBLE, ma200_dev DOUBLE, ma75_dev DOUBLE, ma25_dev DOUBLE, rsi_14 DOUBLE,
            topix_rel_20 DOUBLE, sector_rel_20 DOUBLE, quality_score DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE ai_scores (date DATE, code VARCHAR, ai_score DOUBLE)
    """)
    conn.execute("""
        CREATE TABLE signals (
            date DATE, code VARCHAR, side VARCHAR, score DOUBLE,
            signal_rank INTEGER, size_multiplier DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE positions (date DATE, code VARCHAR, position_size INTEGER, avg_price DOUBLE)
    """)
    conn.execute("""
        CREATE TABLE position_entries (
            code VARCHAR, entry_date DATE, sell_date DATE
        )
    """)
    conn.execute("""
        CREATE TABLE prices_daily (date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE)
    """)
    conn.execute("""
        CREATE TABLE market_regime (date DATE, regime_label VARCHAR)
    """)
    conn.execute("""
        CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)
    """)
    conn.execute("""
        CREATE TABLE stocks (code VARCHAR, sector VARCHAR)
    """)
    conn.execute("""
        CREATE TABLE earnings_calendar (code VARCHAR, announcement_date DATE)
    """)
    conn.execute("""
        CREATE TABLE trading_calendar (date DATE)
    """)
    return conn


class TestGenerateSignalsConfigWeights:
    """When weights=None, config weights are used."""

    def test_config_weights_used_when_none(self, tmp_path):
        """Config momentum weight=0.99 should produce higher scores for momentum stocks."""
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.99
                value: 0.00
                volatility: 0.00
                liquidity: 0.00
                news: 0.01
              threshold: 0.50
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)
        # Insert one stock with high momentum
        conn.execute(
            "INSERT INTO features VALUES (?, '1001', 3.0, 3.0, 0.0, 0.0, NULL, NULL, NULL, 0.0, NULL, NULL, NULL, NULL, NULL, NULL)",
            [target],
        )

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            count = sg.generate_signals(conn, target, weights=None)

        rows = conn.execute("SELECT code, side FROM signals WHERE date = ?", [target]).fetchall()
        assert count >= 1
        assert any(r[0] == "1001" and r[1] == "buy" for r in rows)

    def test_explicit_weights_override_config(self, tmp_path):
        """Explicit weights parameter overrides config."""
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.99
                value: 0.00
                volatility: 0.00
                liquidity: 0.00
                news: 0.01
              threshold: 0.90
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)
        # volatility_20 = -3.0 → low volatility (good) → _sigmoid(-(-3.0)) ≈ 0.95 > 0.50
        conn.execute(
            "INSERT INTO features VALUES (?, '1001', 0.0, 0.0, -3.0, 0.0, NULL, NULL, NULL, 0.0, NULL, NULL, NULL, NULL, NULL, NULL)",
            [target],
        )

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            # Explicit weights: all volatility → low-volatility stock scores ~0.95 > threshold 0.50
            sg.generate_signals(
                conn,
                target,
                threshold=0.50,
                weights={
                    "momentum": 0.0,
                    "value": 0.0,
                    "volatility": 1.0,
                    "liquidity": 0.0,
                    "news": 0.0,
                },
            )
        rows = conn.execute("SELECT code, side FROM signals WHERE date = ?", [target]).fetchall()
        # With all-volatility weight and low volatility z-score, score should be above 0.5
        assert any(r[0] == "1001" for r in rows)


class TestGenerateSignalsConfigThreshold:
    """When threshold=None, config threshold is used."""

    def test_config_threshold_used_when_none(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.20
                value: 0.20
                volatility: 0.20
                liquidity: 0.20
                news: 0.20
              threshold: 0.99
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)
        # Insert stock with moderate score that would pass 0.60 but not 0.99
        conn.execute(
            "INSERT INTO features VALUES (?, '1001', 0.5, 0.5, 0.0, 0.0, NULL, NULL, NULL, 0.0, NULL, NULL, NULL, NULL, NULL, NULL)",
            [target],
        )

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            # threshold=None → uses config threshold=0.99 → should produce 0 buy signals
            sg.generate_signals(conn, target)

        rows = conn.execute(
            "SELECT code, side FROM signals WHERE date = ? AND side='buy'", [target]
        ).fetchall()
        assert len(rows) == 0

    def test_explicit_threshold_overrides_config(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.20
                value: 0.20
                volatility: 0.20
                liquidity: 0.20
                news: 0.20
              threshold: 0.99
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)
        conn.execute(
            "INSERT INTO features VALUES (?, '1001', 3.0, 3.0, 0.0, 0.0, NULL, NULL, NULL, 0.0, NULL, NULL, NULL, NULL, NULL, NULL)",
            [target],
        )

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            # Explicit threshold=0.10 overrides config 0.99 → should produce buy signal
            sg.generate_signals(conn, target, threshold=0.10)

        rows = conn.execute(
            "SELECT side FROM signals WHERE date = ? AND code='1001'", [target]
        ).fetchall()
        assert any(r[0] == "buy" for r in rows)


class TestGenerateSignalsConfigStopLoss:
    """Config stop_loss_rate is passed to _generate_sell_signals."""

    def test_config_stop_loss_used(self, tmp_path):
        """Very tight stop_loss (-0.01) should trigger SELL for small loss."""
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.20
                value: 0.20
                volatility: 0.20
                liquidity: 0.20
                news: 0.20
              threshold: 0.60
              stop_loss_rate: -0.01
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)

        # Position bought at 1000, now close=985 → -1.5% loss (exceeds -1% stop)
        conn.execute("INSERT INTO positions VALUES (?, '1001', 100, 1000.0)", [target])
        conn.execute(
            "INSERT INTO prices_daily VALUES (?, '1001', 985.0, 990.0, 980.0, 985.0)",
            [target],
        )
        conn.execute("INSERT INTO trading_calendar VALUES (?)", [target])

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            sg.generate_signals(conn, target)

        rows = conn.execute("SELECT code, side FROM signals WHERE date = ?", [target]).fetchall()
        assert any(r[0] == "1001" and r[1] == "sell" for r in rows)


class TestGenerateSignalsNoneResolution:
    """All None params resolve from config without raising."""

    def test_all_none_params_no_error(self, tmp_path):
        """generate_signals() with all None params completes without error."""
        yaml_content = textwrap.dedent("""\
            strategy:
              weights:
                momentum: 0.40
                value: 0.20
                volatility: 0.15
                liquidity: 0.15
                news: 0.10
              threshold: 0.60
              stop_loss_rate: -0.08
              min_holding_days: 5
              max_holding_days: 60
              trailing_stop_atr_mult: 2.0
              reentry_cooldown_days: 5
              gap_up_threshold: 0.05
              gap_down_threshold: -0.03
            value_score:
              weights:
                per: 0.50
                pbr: 0.30
                div_yield: 0.20
              normalization:
                per_mid: 20.0
                pbr_mid: 1.5
                div_yield_max: 3.0
        """)
        cfg_path = tmp_path / "strategy_config.yaml"
        cfg_path.write_text(yaml_content, encoding="utf-8")

        conn = _make_db()
        target = date(2025, 1, 6)

        from kabusys.strategy import signal_generator as sg

        with patch.object(sg, "_STRATEGY_CONFIG_PATH", cfg_path):
            count = sg.generate_signals(
                conn,
                target,
                threshold=None,
                weights=None,
                min_holding_days=None,
                max_holding_days=None,
                trailing_stop_atr=None,
            )
        assert count == 0  # no features/positions inserted, so 0 signals
