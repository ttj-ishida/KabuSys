"""job_run_recorder モジュールのテスト"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from kabusys.operations.night_batch_report import JobRunResult


def _make_result(
    job_name: str = "data_update_job",
    status: str = "success",
    started_at: datetime | None = None,
) -> JobRunResult:
    dt = started_at or datetime(2026, 5, 7, 15, 30, 0, tzinfo=timezone.utc)
    return JobRunResult(
        job_name=job_name,
        status=status,
        started_at=dt,
        finished_at=datetime(2026, 5, 7, 15, 31, 0, tzinfo=timezone.utc),
        duration_sec=60.0,
        updated_rows={"prices_daily": 1850},
        warnings=[],
        errors=[],
    )


def test_write_creates_file(tmp_path):
    from kabusys.operations.job_run_recorder import write_job_result

    result = _make_result()
    path = write_job_result(result, base_dir=tmp_path, run_date=date(2026, 5, 7))
    assert path.exists()
    assert path.name == "data_update_job.json"
    assert path.parent.name == "2026-05-07"


def test_write_json_content(tmp_path):
    from kabusys.operations.job_run_recorder import write_job_result

    result = _make_result()
    path = write_job_result(result, base_dir=tmp_path, run_date=date(2026, 5, 7))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["job_name"] == "data_update_job"
    assert data["status"] == "success"
    assert data["updated_rows"] == {"prices_daily": 1850}
    assert data["duration_sec"] == 60.0
    assert "started_at" in data
    assert "finished_at" in data


def test_read_empty_dir_returns_empty(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results

    results = read_job_results(date(2026, 5, 7), base_dir=tmp_path)
    assert results == []


def test_read_nonexistent_dir_returns_empty(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results

    results = read_job_results(date(2099, 1, 1), base_dir=tmp_path)
    assert results == []


def test_write_then_read_roundtrip(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results, write_job_result

    result = _make_result(status="failed")
    result.errors.append("something went wrong")
    write_job_result(result, base_dir=tmp_path, run_date=date(2026, 5, 7))
    loaded = read_job_results(date(2026, 5, 7), base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].job_name == "data_update_job"
    assert loaded[0].status == "failed"
    assert loaded[0].errors == ["something went wrong"]
    assert loaded[0].updated_rows == {"prices_daily": 1850}


def test_read_multiple_jobs(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results, write_job_result

    for job_name in [
        "data_update_job",
        "feature_generation_job",
        "strategy_signal_job",
    ]:
        write_job_result(
            _make_result(job_name=job_name),
            base_dir=tmp_path,
            run_date=date(2026, 5, 7),
        )
    loaded = read_job_results(date(2026, 5, 7), base_dir=tmp_path)
    assert len(loaded) == 3
    names = {r.job_name for r in loaded}
    assert names == {"data_update_job", "feature_generation_job", "strategy_signal_job"}


def test_read_skips_malformed_json(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results, write_job_result

    write_job_result(_make_result(), base_dir=tmp_path, run_date=date(2026, 5, 7))
    bad = tmp_path / "2026-05-07" / "broken_job.json"
    bad.write_text("not valid json", encoding="utf-8")
    loaded = read_job_results(date(2026, 5, 7), base_dir=tmp_path)
    assert len(loaded) == 1


def test_write_overwrites_same_job(tmp_path):
    from kabusys.operations.job_run_recorder import read_job_results, write_job_result

    write_job_result(_make_result(status="failed"), base_dir=tmp_path, run_date=date(2026, 5, 7))
    write_job_result(_make_result(status="success"), base_dir=tmp_path, run_date=date(2026, 5, 7))
    loaded = read_job_results(date(2026, 5, 7), base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].status == "success"
