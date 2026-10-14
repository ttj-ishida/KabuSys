"""ENABLE_AUTO_EXECUTION フラグによる自動執行ジョブの有効/無効切り替えテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_scheduler  # noqa: E402

_AUTO_EXEC_JOBS = {"execution_start", "position_reconciliation_report", "monitoring_start"}


def _jobs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_text: str | None) -> dict:
    if env_text is not None:
        (tmp_path / ".env").write_text(env_text, encoding="utf-8")
    monkeypatch.setattr(run_scheduler, "_PROJECT_ROOT", tmp_path)
    return {j.name: j for j in run_scheduler._build_job_schedule()}


def test_auto_execution_enabled_by_default(monkeypatch, tmp_path):
    """フラグ未設定（.env なし）では従来どおり自動執行ジョブが有効。"""
    jobs = _jobs(monkeypatch, tmp_path, None)
    assert all(jobs[name].enabled for name in _AUTO_EXEC_JOBS)


def test_auto_execution_disabled_by_flag(monkeypatch, tmp_path):
    """ENABLE_AUTO_EXECUTION=false で執行起動・かぶステ必須のレポート・執行監視を無効化する。"""
    jobs = _jobs(monkeypatch, tmp_path, "ENABLE_AUTO_EXECUTION=false\n")
    assert not any(jobs[name].enabled for name in _AUTO_EXEC_JOBS)
    # 手動運用で必要なジョブは引き続き有効
    for name in (
        "pre_market_report",
        "manual_order_report_morning",
        "data_update",
        "strategy_signal",
        "portfolio_construction",
        "manual_order_report_evening",
    ):
        assert jobs[name].enabled, name


def test_auto_execution_explicit_true(monkeypatch, tmp_path):
    jobs = _jobs(monkeypatch, tmp_path, "ENABLE_AUTO_EXECUTION=true\n")
    assert all(jobs[name].enabled for name in _AUTO_EXEC_JOBS)
