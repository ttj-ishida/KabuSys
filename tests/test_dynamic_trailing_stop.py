"""tests/test_dynamic_trailing_stop.py — 多段階トレーリングストップ テスト"""

from __future__ import annotations

import inspect

import pytest

from kabusys.backtest.engine import run_backtest
from kabusys.strategy.signal_generator import generate_signals


class TestDynamicTrailingStopSignature:
    def test_generate_signals_has_dynamic_trailing_stop(self):
        sig = inspect.signature(generate_signals)
        assert "dynamic_trailing_stop" in sig.parameters

    def test_generate_signals_dynamic_trailing_stop_default_false(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["dynamic_trailing_stop"].default is False

    def test_generate_signals_has_trail_profit_gate_atr(self):
        sig = inspect.signature(generate_signals)
        assert "trail_profit_gate_atr" in sig.parameters

    def test_generate_signals_trail_profit_gate_atr_default_1_5(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_profit_gate_atr"].default == pytest.approx(1.5)

    def test_generate_signals_has_trail_stage2_mult(self):
        sig = inspect.signature(generate_signals)
        assert "trail_stage2_mult" in sig.parameters

    def test_generate_signals_trail_stage2_mult_default_1_5(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_stage2_mult"].default == pytest.approx(1.5)

    def test_generate_signals_has_trail_stage3_mult(self):
        sig = inspect.signature(generate_signals)
        assert "trail_stage3_mult" in sig.parameters

    def test_generate_signals_trail_stage3_mult_default_1_0(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_stage3_mult"].default == pytest.approx(1.0)

    def test_run_backtest_has_dynamic_trailing_stop(self):
        sig = inspect.signature(run_backtest)
        assert "dynamic_trailing_stop" in sig.parameters

    def test_run_backtest_dynamic_trailing_stop_default_false(self):
        sig = inspect.signature(run_backtest)
        assert sig.parameters["dynamic_trailing_stop"].default is False

    def test_run_backtest_has_trail_profit_gate_atr(self):
        sig = inspect.signature(run_backtest)
        assert "trail_profit_gate_atr" in sig.parameters

    def test_run_backtest_has_trail_stage2_mult(self):
        sig = inspect.signature(run_backtest)
        assert "trail_stage2_mult" in sig.parameters

    def test_run_backtest_has_trail_stage3_mult(self):
        sig = inspect.signature(run_backtest)
        assert "trail_stage3_mult" in sig.parameters
