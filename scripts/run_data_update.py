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
from kabusys.data.breadth import calc_and_save_breadth
from kabusys.data.pipeline import run_daily_etl
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="data_update")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    try:
        # ETL: 当日の価格データを取得して prices_daily に追加
        result = run_daily_etl(conn)
        if result.errors:
            logger.warning("ETL 完了（エラーあり）: %s", result.errors)
        else:
            logger.info("ETL 完了")

        # ETL で挿入された最新日付の翌日を target_date として breadth を計算
        # （prices_daily の date < target_date = 当日以前のデータを使用）
        max_date_row = conn.execute(
            "SELECT MAX(date) FROM prices_daily"
        ).fetchone()
        if max_date_row and max_date_row[0]:
            target_date = max_date_row[0]
            breadth_result = calc_and_save_breadth(conn, target_date)
            logger.info(
                "breadth 計算完了: date=%s result=%d", target_date, breadth_result
            )
        else:
            logger.warning("breadth 計算スキップ: prices_daily にデータなし")
    except Exception:
        logger.exception("data_update バッチが失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
