# scripts/run_feature_gen.py
"""Night batch: 特徴量生成 (feature_generation_job)。

Task Scheduler から 16:00 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.feature_engineering import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        target_date = date.today()
        n = build_features(conn, target_date)
        logger.info("特徴量生成完了: %d 件 (date=%s)", n, target_date)
    except Exception:
        logger.exception("build_features が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
