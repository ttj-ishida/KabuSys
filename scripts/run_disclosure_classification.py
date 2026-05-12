# scripts/run_disclosure_classification.py
"""Night batch: 適時開示イベント分類 (disclosure_classification_job)。

Task Scheduler から 17:00 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.disclosure_classifier import run_disclosure_classification
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="disclosure_classification", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "disclosure_classification_job"
_APP_NAME = "disclosure_classification"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    _failed = False
    try:
        settings = Settings()
        if not settings.enable_tdnet:
            logger.info("TDnet 収集はオプション機能です（ENABLE_TDNET=false）。スキップします。")
            return
        conn = duckdb.connect(str(settings.duckdb_path))
        saved = run_disclosure_classification(conn)
        logger.info("disclosure_classification 完了: saved=%d", saved)
    except Exception:
        logger.exception("disclosure_classification バッチが失敗しました")
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        if run_id is not None:
            try:
                update_process(run_id, status="failed" if _failed else "success")
            except Exception:
                logger.warning("process_registry 更新に失敗しました", exc_info=True)
        log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
