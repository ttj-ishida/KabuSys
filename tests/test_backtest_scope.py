"""tests/test_backtest_scope.py — BacktestScope / BacktestResult メタデータ テスト"""

from __future__ import annotations

import contextlib
import io
from datetime import date
from unittest.mock import patch

import pytest

from kabusys.data.schema import init_schema
from kabusys.backtest.engine import BacktestResult, BacktestScope
from kabusys.backtest.metrics import BacktestMetrics


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


SCOPE_DATE = date(2026, 4, 1)


@pytest.fixture
def bt_conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _insert_feature(conn, code: str, d: date) -> None:
    """高スコアの features 行を挿入する。"""
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, 3.0, 3.0, -3.0, 3.0, 5.0, 3.0)",
        [d, code],
    )


def _insert_regime(conn, d: date, label: str = "bull") -> None:
    score = 0.5 if label == "bull" else -0.5
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, score, label],
    )


def _insert_breadth(conn, d: date, stop: bool = False) -> None:
    conn.execute(
        "INSERT INTO market_breadth (date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, ?, ?)",
        [d, 100.0, 0.5, stop],
    )


class TestGenerateSignalsScope:
    def test_scope_none_generates_all_codes(self, bt_conn):
        """scope=None → 既存動作と変わらず全銘柄でシグナル生成。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678", "9999"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        generate_signals(bt_conn, SCOPE_DATE, scope=None)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert {"1234", "5678", "9999"}.issubset(codes)

    def test_scope_manual_codes_excludes_out_of_scope(self, bt_conn):
        """`mode='manual_codes'` → scope.codes 外の銘柄はシグナルに含まれない。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678", "9999"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="manual_codes", codes=["1234", "5678"])
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert "9999" not in codes, "scope 外の銘柄がシグナルに含まれている"
        assert codes.intersection({"1234", "5678"}), "scope 内銘柄のシグナルがない"

    def test_scope_default_universe_same_as_none(self, bt_conn):
        """`mode='default_universe'` → scope=None と同じく全銘柄が対象。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="default_universe")
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        codes = {r[0] for r in rows}
        assert "1234" in codes
        assert "5678" in codes

    def test_scope_empty_codes_generates_no_buy(self, bt_conn):
        """`codes=[]` → features フィルタが空集合 → BUY シグナルなし。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(bt_conn, SCOPE_DATE)
        _insert_breadth(bt_conn, SCOPE_DATE)
        for code in ["1234", "5678"]:
            _insert_feature(bt_conn, code, SCOPE_DATE)

        scope = BacktestScope(mode="manual_codes", codes=[])
        generate_signals(bt_conn, SCOPE_DATE, scope=scope)

        rows = bt_conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [SCOPE_DATE]
        ).fetchall()
        assert len(rows) == 0
