"""tests/test_kill_switch.py — KillSwitch ユニットテスト"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kabusys.monitoring.kill_switch import KillSwitch
from kabusys.monitoring.system_monitor import SystemCheckResult
from kabusys.monitoring.trade_monitor import TradeCheckResult
from kabusys.monitoring.risk_monitor import RiskCheckResult


def _make_sys(process_ok: bool = True, data_freshness_ok: bool = True) -> SystemCheckResult:
    return SystemCheckResult(
        recorded_at="2026-04-02T09:05:00+09:00",
        cpu_percent=30.0,
        memory_percent=50.0,
        disk_percent=40.0,
        process_ok=process_ok,
        data_freshness_ok=data_freshness_ok,
        stale_pid_detected=False,
    )


def _make_trade(stale: list[str] | None = None, anomaly: list[str] | None = None) -> TradeCheckResult:
    return TradeCheckResult(
        logged_at="2026-04-02T09:05:00+09:00",
        stale_orders=stale or [],
        anomaly_fills=anomaly or [],
    )


def _make_risk(drawdown_alert: bool = False, position_limit_alert: bool = False,
               drawdown_pct: float = 0.0, position_count: int = 0) -> RiskCheckResult:
    return RiskCheckResult(
        logged_at="2026-04-02T09:05:00+09:00",
        drawdown_pct=drawdown_pct,
        drawdown_alert=drawdown_alert,
        position_count=position_count,
        position_limit_alert=position_limit_alert,
    )


class TestKillSwitchEvaluate:

    def test_drawdown_alert_writes_flag_and_returns_reason(self, tmp_path):
        """drawdown_alert=True → kill.flag 書き込み・理由文字列返却"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, drawdown_pct=0.123),
        )
        assert reason is not None
        assert "DRAWDOWN" in reason
        assert (tmp_path / "kill.flag").exists()

    def test_position_limit_alert_writes_flag(self, tmp_path):
        """position_limit_alert=True → kill.flag 書き込み"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(position_limit_alert=True, position_count=11),
        )
        assert reason is not None
        assert (tmp_path / "kill.flag").exists()

    def test_process_ok_false_does_not_write_flag(self, tmp_path):
        """process_ok=False のみ → kill.flag 書き込まない・None 返却"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(process_ok=False),
            _make_trade(),
            _make_risk(),
        )
        assert reason is None
        assert not (tmp_path / "kill.flag").exists()

    def test_idempotent_does_not_overwrite_existing_flag(self, tmp_path):
        """flag が既存の場合は再書き込みしない（冪等）"""
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("original content")
        ks = KillSwitch(flag_path=flag_path)
        ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, drawdown_pct=0.15),
        )
        assert flag_path.read_text() == "original content"

    def test_all_false_returns_none_no_flag(self, tmp_path):
        """全条件 False → None 返却・flag 作成なし"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(_make_sys(), _make_trade(), _make_risk())
        assert reason is None
        assert not (tmp_path / "kill.flag").exists()

    def test_drawdown_evaluated_before_position_limit(self, tmp_path):
        """両方 True の場合 drawdown_alert が先（評価順序）"""
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        reason = ks.evaluate(
            _make_sys(),
            _make_trade(),
            _make_risk(drawdown_alert=True, position_limit_alert=True, drawdown_pct=0.12),
        )
        assert reason is not None
        assert "DRAWDOWN" in reason


class TestKillSwitchIsFlaggedAndClear:

    def test_is_flagged_true_when_flag_exists(self, tmp_path):
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("test")
        ks = KillSwitch(flag_path=flag_path)
        assert ks.is_flagged() is True

    def test_is_flagged_false_when_no_flag(self, tmp_path):
        ks = KillSwitch(flag_path=tmp_path / "kill.flag")
        assert ks.is_flagged() is False

    def test_clear_removes_flag(self, tmp_path):
        flag_path = tmp_path / "kill.flag"
        flag_path.write_text("test")
        ks = KillSwitch(flag_path=flag_path)
        ks.clear()
        assert not flag_path.exists()
