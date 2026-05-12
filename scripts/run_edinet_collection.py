# scripts/run_edinet_collection.py
"""Night batch: EDINET 法定開示収集 (edinet_collection_job)。

Task Scheduler から 18:00 頃に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.edinet_collector import run_edinet_collection
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

setup_logging(app_name="edinet_collection")
logger = logging.getLogger(__name__)

_APP_NAME = "edinet_collection"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    conn = None
    _failed = False
    try:
        settings = Settings()
        if not settings.enable_edinet:
            logger.info("EDINET 収集はオプション機能です（ENABLE_EDINET=false）。スキップします。")
            return
        if not settings.edinet_api_key:
            logger.error(
                "ENABLE_EDINET=true ですが EDINET_API_KEY が未設定です。"
                ".env に EDINET_API_KEY を設定してください。"
            )
            _failed = True
            return
        conn = duckdb.connect(str(settings.duckdb_path))
        saved = run_edinet_collection(conn, api_key=settings.edinet_api_key)
        logger.info("edinet_collection 完了: saved=%d", saved)
    except Exception:
        logger.exception("edinet_collection バッチが失敗しました")
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
        if _failed:
            sys.exit(1)


if __name__ == "__main__":
    main()
