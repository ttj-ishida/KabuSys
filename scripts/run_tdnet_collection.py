# scripts/run_tdnet_collection.py
"""Night batch: TDnet 適時開示収集 (tdnet_collection_job)。

Task Scheduler から 15:35 に起動される。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.tdnet_collector import run_tdnet_collection
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="tdnet_collection")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    if not settings.enable_tdnet:
        logger.info(
            "TDnet 収集はオプション機能です（ENABLE_TDNET=false）。スキップします。"
        )
        return
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        saved = run_tdnet_collection(conn)
        logger.info("tdnet_collection 完了: saved=%d", saved)
    except Exception:
        logger.exception("tdnet_collection バッチが失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
