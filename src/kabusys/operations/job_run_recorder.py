"""JobRunResult を artifacts/job_runs/{date}/ に書き出す・読み込むヘルパー。"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

from kabusys.operations.night_batch_report import JobRunResult

logger = logging.getLogger(__name__)

_DEFAULT_BASE = Path("artifacts") / "job_runs"


def write_job_result(
    result: JobRunResult,
    base_dir: Path | None = None,
    run_date: date | None = None,
) -> Path:
    """artifacts/job_runs/{run_date}/{job_name}.json に書き出す。

    run_date 未指定時は date.today() を使用する。
    同名ファイルが存在する場合は上書きする。

    Returns:
        書き出したファイルパス。
    """
    base = base_dir if base_dir is not None else _DEFAULT_BASE
    d = (run_date or date.today()).isoformat()
    out_dir = base / d
    out_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "job_name": result.job_name,
        "status": result.status,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "duration_sec": result.duration_sec,
        "updated_rows": result.updated_rows,
        "warnings": result.warnings,
        "errors": result.errors,
    }
    path = out_dir / f"{result.job_name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_job_results(
    run_date: date,
    base_dir: Path | None = None,
) -> list[JobRunResult]:
    """artifacts/job_runs/{run_date}/ の全 JSON を JobRunResult リストに変換して返す。

    ディレクトリが存在しない場合・ファイルが 0 件の場合は空リストを返す。
    読み込みに失敗した個別ファイルは警告ログを出してスキップする。
    """
    base = base_dir if base_dir is not None else _DEFAULT_BASE
    run_dir = base / run_date.isoformat()
    if not run_dir.exists():
        return []

    results: list[JobRunResult] = []
    for path in sorted(run_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append(
                JobRunResult(
                    job_name=data["job_name"],
                    status=data["status"],
                    started_at=datetime.fromisoformat(data["started_at"]),
                    finished_at=datetime.fromisoformat(data["finished_at"]),
                    duration_sec=float(data["duration_sec"]),
                    updated_rows={k: int(v) for k, v in data.get("updated_rows", {}).items()},
                    warnings=list(data.get("warnings", [])),
                    errors=list(data.get("errors", [])),
                )
            )
        except Exception:  # JSONDecodeError, KeyError, ValueError, or any future field change
            logger.warning("job result JSON の読み込みに失敗しました: %s", path, exc_info=True)
    return results
