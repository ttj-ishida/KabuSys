"""#428: EDINET 収集・適時開示分類ジョブのスケジュール登録テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_scheduler  # noqa: E402


def _jobs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_text: str) -> dict:
    (tmp_path / ".env").write_text(env_text, encoding="utf-8")
    monkeypatch.setattr(run_scheduler, "_PROJECT_ROOT", tmp_path)
    return {j.name: j for j in run_scheduler._build_job_schedule()}


def test_disclosure_jobs_registered_and_enabled_by_flags(monkeypatch, tmp_path):
    jobs = _jobs(monkeypatch, tmp_path, "ENABLE_TDNET=true\nENABLE_EDINET=true\n")
    dc = jobs["disclosure_classification"]
    assert (dc.script, dc.trigger_hour, dc.trigger_minute, dc.needs_exclusive_db) == (
        "run_disclosure_classification.py",
        15,
        45,
        True,
    )
    assert dc.enabled
    ed = jobs["edinet_collection"]
    assert (ed.script, ed.trigger_hour, ed.trigger_minute, ed.needs_exclusive_db) == (
        "run_edinet_collection.py",
        17,
        45,
        True,
    )
    assert ed.enabled


def test_disclosure_jobs_follow_flags(monkeypatch, tmp_path):
    jobs = _jobs(monkeypatch, tmp_path, "ENABLE_TDNET=false\nENABLE_EDINET=false\n")
    assert not jobs["disclosure_classification"].enabled
    assert not jobs["edinet_collection"].enabled


def test_task_scheduler_ps1_registers_disclosure_jobs():
    ps1 = (Path(__file__).resolve().parents[1] / "scripts" / "setup_task_scheduler.ps1").read_text(
        encoding="utf-8"
    )
    assert "run_disclosure_classification.py" in ps1 and '"15:45"' in ps1
    assert "run_edinet_collection.py" in ps1 and '"17:45"' in ps1
