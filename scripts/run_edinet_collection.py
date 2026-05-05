# scripts/run_edinet_collection.py
"""Night batch: EDINET 法定開示収集 (edinet_collection_job)。

Task Scheduler から 18:00 頃に起動される。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.edinet_collector import run_edinet_collection
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="edinet_collection")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    if not settings.enable_edinet:
        logger.info(
            "EDINET 収集はオプション機能です（ENABLE_EDINET=false）。スキップします。"
        )
        return
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        saved = run_edinet_collection(conn, api_key=settings.edinet_api_key)
        logger.info("edinet_collection 完了: saved=%d", saved)
    except Exception:
        logger.exception("edinet_collection バッチが失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
