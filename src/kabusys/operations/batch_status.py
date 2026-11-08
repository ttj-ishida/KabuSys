"""夜間バッチの成否判定ヘルパー（#421 / #426 で共有）。

シグナルが 0 件の日は signals / signal_queue に行が作られないため、行の有無では
「バッチ欠落」と「正常だがシグナルなし」を区別できない。ジョブ実行記録
（artifacts/job_runs/{date}/*.json）で区別する。
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from kabusys.operations.job_run_recorder import _DEFAULT_BASE

logger = logging.getLogger(__name__)

SIGNAL_BATCH_JOBS: tuple[str, ...] = ("strategy_signal_job", "portfolio_construction_job")
_OK_STATUSES = ("success", "warning")


def signal_batch_succeeded(run_date: date, base_dir: Path | None = None) -> bool:
    """run_date のシグナル生成バッチ（strategy_signal + portfolio_construction）が成功したか。

    両ジョブの記録が存在し、status が success / warning の場合のみ True。
    記録なし・読み込み不能・failed / skipped は False。
    """
    base = base_dir if base_dir is not None else _DEFAULT_BASE
    run_dir = base / run_date.isoformat()
    for name in SIGNAL_BATCH_JOBS:
        try:
            data = json.loads((run_dir / f"{name}.json").read_text(encoding="utf-8"))
            status = data["status"]
        except Exception:
            logger.debug("ジョブ記録を読めません: %s/%s.json", run_dir, name, exc_info=True)
            return False
        if status not in _OK_STATUSES:
            return False
    return True
