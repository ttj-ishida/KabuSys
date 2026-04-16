# scripts/rebuild_features.py
"""特徴量を手動で再計算するメンテナンススクリプト。

prices_daily に当日データが存在することを確認してから build_features() を実行する。
使い方: python scripts/rebuild_features.py
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()

    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM prices_daily WHERE date = ?", [target_date]
        )
        count = cursor.fetchone()[0]
        if count == 0:
            logger.error(
                "本日 (%s) の prices_daily データが存在しません。"
                "先に run_data_update.py を実行してください。",
                target_date,
            )
            sys.exit(1)

        n = build_features(conn, target_date)
        logger.info("特徴量再計算完了: %d 件 (date=%s)", n, target_date)

    except SystemExit:
        raise
    except Exception:
        logger.exception("rebuild_features が失敗しました")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
