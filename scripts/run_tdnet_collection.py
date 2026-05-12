# scripts/run_tdnet_collection.py
"""Night batch: TDnet 適時開示収集 (tdnet_collection_job)。

Task Scheduler から 15:35 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.tdnet_collector import run_tdnet_collection
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

setup_logging(app_name="tdnet_collection")
logger = logging.getLogger(__name__)

_APP_NAME = "tdnet_collection"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    settings = Settings()
    if not settings.enable_tdnet:
        logger.info("TDnet 収集はオプション機能です（ENABLE_TDNET=false）。スキップします。")
        log_run_end(_APP_NAME, status="success", started_at=started_at)
        return
    conn = duckdb.connect(str(settings.duckdb_path))
    _failed = False
    try:
        saved = run_tdnet_collection(conn)
        logger.info("tdnet_collection 完了: saved=%d", saved)
    except Exception:
        logger.exception("tdnet_collection バッチが失敗しました")
        _failed = True
    finally:
        conn.close()
    log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
