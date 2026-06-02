# scripts/rebuild_features.py
"""特徴量を手動で再計算するメンテナンススクリプト。

prices_daily に対象日データが存在することを確認してから build_features() を実行する。
使い方: python scripts/rebuild_features.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.strategy.feature_engineering import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="特徴量を手動で再計算します。")
    parser.add_argument(
        "--date",
        dest="target_date",
        help="再計算対象日 (YYYY-MM-DD)。省略時は本日、データ未着なら最新 prices_daily 日。",
    )
    return parser.parse_args()


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        logger.error("--date は YYYY-MM-DD 形式で指定してください: %s", value)
        sys.exit(2)


def _price_count(conn: duckdb.DuckDBPyConnection, target_date: date) -> int:
    cursor = conn.execute("SELECT COUNT(*) FROM prices_daily WHERE date = ?", [target_date])
    return int(cursor.fetchone()[0])


def _latest_price_date(conn: duckdb.DuckDBPyConnection, upper_bound: date) -> date | None:
    row = conn.execute(
        "SELECT MAX(date) FROM prices_daily WHERE date <= ?",
        [upper_bound],
    ).fetchone()
    return row[0] if row else None


def main() -> None:
    args = _parse_args()
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    today = date.today()
    target_date = _parse_date(args.target_date) if args.target_date else today

    try:
        count = _price_count(conn, target_date)
        if count == 0:
            if args.target_date:
                logger.error(
                    "指定日 (%s) の prices_daily データが存在しません。",
                    target_date,
                )
                sys.exit(1)

            latest = _latest_price_date(conn, today)
            if latest is None:
                logger.error(
                    "prices_daily データが存在しません。先に run_data_update.py を実行してください。"
                )
                sys.exit(1)

            logger.warning(
                "本日 (%s) の prices_daily データが存在しないため、最新日 (%s) で再計算します。",
                today,
                latest,
            )
            target_date = latest

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
