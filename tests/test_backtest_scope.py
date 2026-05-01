"""tests/test_backtest_scope.py — BacktestScope / BacktestResult メタデータ テスト"""

from __future__ import annotations

import contextlib
import io
from datetime import date
from unittest.mock import patch

import pytest

from kabusys.backtest.engine import BacktestResult, BacktestScope
from kabusys.backtest.metrics import BacktestMetrics
from kabusys.data.schema import init_schema


def _make_metrics() -> BacktestMetrics:
    return BacktestMetrics(
        cagr=0.0,
        sharpe_ratio=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        payoff_ratio=0.0,
        total_trades=0,
    )


class TestBacktestScope:
    def test_default_universe_defaults(self):
        """mode='default_universe' のデフォルト値を検証する。"""
        scope = BacktestScope(mode="default_universe")
        assert scope.mode == "default_universe"
        assert scope.codes is None
        assert scope.preserve_universe_filters is True

    def test_manual_codes_mode(self):
        """`mode='manual_codes'` + コード指定が正しく保持される。"""
        scope = BacktestScope(mode="manual_codes", codes=["1234", "5678"])
        assert scope.mode == "manual_codes"
        assert scope.codes == ["1234", "5678"]

    def test_preserve_filters_false(self):
        """`preserve_universe_filters=False` が保持される。"""
        scope = BacktestScope(
            mode="manual_codes", codes=["1234"], preserve_universe_filters=False
        )
        assert scope.preserve_universe_filters is False


class TestBacktestResultMetadata:
    def test_result_default_scope_fields(self):
        """`BacktestResult` がスコープメタデータフィールドをデフォルト値で持つ。"""
        result = BacktestResult(history=[], trades=[], metrics=_make_metrics())
        assert result.scope_mode == "default_universe"
        assert result.scope_codes is None
        assert result.preserve_universe_filters is True
        assert result.effective_universe_size is None
        assert result.excluded_codes == []
        assert result.excluded_reasons == {}

    def test_result_scope_fields_can_be_set(self):
        """スコープメタデータがコンストラクタで設定できる。"""
        result = BacktestResult(
            history=[],
            trades=[],
            metrics=_make_metrics(),
            scope_mode="manual_codes",
            scope_codes=["1234", "5678"],
            preserve_universe_filters=False,
            effective_universe_size=2,
            excluded_codes=["9999"],
            excluded_reasons={"9999": "not in features (universe filter)"},
        )
        assert result.scope_mode == "manual_codes"
        assert result.scope_codes == ["1234", "5678"]
        assert result.preserve_universe_filters is False
        assert result.effective_universe_size == 2
        assert result.excluded_codes == ["9999"]
        assert result.excluded_reasons == {"9999": "not in features (universe filter)"}
