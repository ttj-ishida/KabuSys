"""夜間バッチ成否判定ヘルパー（#421 / #426）のテスト。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from kabusys.operations.batch_status import signal_batch_succeeded

D = date(2026, 10, 14)


def _write(base: Path, name: str, status: str) -> None:
    d = base / D.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"job_name": name, "status": status}))


def test_true_when_both_success_or_warning(tmp_path):
    _write(tmp_path, "strategy_signal_job", "success")
    _write(tmp_path, "portfolio_construction_job", "warning")
    assert signal_batch_succeeded(D, tmp_path) is True


def test_false_when_one_missing(tmp_path):
    _write(tmp_path, "strategy_signal_job", "success")
    assert signal_batch_succeeded(D, tmp_path) is False


def test_false_when_failed_or_skipped(tmp_path):
    _write(tmp_path, "strategy_signal_job", "success")
    _write(tmp_path, "portfolio_construction_job", "failed")
    assert signal_batch_succeeded(D, tmp_path) is False
    _write(tmp_path, "portfolio_construction_job", "skipped")
    assert signal_batch_succeeded(D, tmp_path) is False


def test_false_when_dir_missing_or_unreadable(tmp_path):
    assert signal_batch_succeeded(D, tmp_path) is False
    _write(tmp_path, "strategy_signal_job", "success")
    (tmp_path / D.isoformat() / "portfolio_construction_job.json").write_text("{not json")
    assert signal_batch_succeeded(D, tmp_path) is False
