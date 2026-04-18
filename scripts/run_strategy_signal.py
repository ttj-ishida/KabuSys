# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.signal_generator import generate_signals
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="strategy_signal")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        target_date = date.today()
        n = generate_signals(conn, target_date)
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
    except Exception:
        logger.exception("generate_signals が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
