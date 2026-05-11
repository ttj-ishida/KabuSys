# scripts/run_disclosure_classification.py
"""Night batch: 適時開示イベント分類 (disclosure_classification_job)。

Task Scheduler から 17:00 に起動される。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.disclosure_classifier import run_disclosure_classification
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="disclosure_classification")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    if not settings.enable_tdnet:
        logger.info("TDnet 収集はオプション機能です（ENABLE_TDNET=false）。スキップします。")
        return
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        saved = run_disclosure_classification(conn)
        logger.info("disclosure_classification 完了: saved=%d", saved)
    except Exception:
        logger.exception("disclosure_classification バッチが失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
