# scripts/run_data_update.py
"""Night batch: 日次市場データ更新 (data_update_job)。

Task Scheduler から 15:30 に起動される。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.pipeline import run_daily_etl
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="data_update")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        result = run_daily_etl(conn)
        if result.errors:
            logger.warning("ETL 完了（エラーあり）: %s", result.errors)
        else:
            logger.info("ETL 完了")
    except Exception:
        logger.exception("run_daily_etl が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
