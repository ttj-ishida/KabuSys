"""DB 初期化スクリプト。

DuckDB（分析用）と SQLite（監視用・ペーパートレード用）のスキーマを作成する。
既にテーブルが存在する場合はスキップ（冪等）。

Usage:
    python scripts/setup_db.py
    python scripts/setup_db.py --paper   # paper_trading.db も初期化
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加（scripts/ から実行する場合）
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="KabuSys DB 初期化スクリプト")
    parser.add_argument(
        "--paper",
        action="store_true",
        help="paper_trading.db も初期化する",
    )
    args = parser.parse_args()

    from kabusys.config import Settings
    from kabusys.data.schema import init_schema
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    from kabusys.execution.order_repository import init_orders_db

    settings = Settings()

    # --- DuckDB ---
    duckdb_path = settings.duckdb_path
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("DuckDB を初期化します: %s", duckdb_path)
    conn = init_schema(duckdb_path)
    conn.close()
    logger.info("DuckDB 初期化完了")

    # --- SQLite (monitoring) ---
    sqlite_path = settings.sqlite_path
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("SQLite (monitoring) を初期化します: %s", sqlite_path)
    with sqlite3.connect(sqlite_path) as sqlite_conn:
        init_monitoring_db(sqlite_conn)
    logger.info("SQLite (monitoring) 初期化完了")

    # --- SQLite (paper_trading) ---
    if args.paper:
        paper_path = settings.paper_sqlite_path
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("SQLite (paper_trading) を初期化します: %s", paper_path)
        with sqlite3.connect(paper_path) as paper_conn:
            init_orders_db(paper_conn)
            init_monitoring_db(paper_conn)
        logger.info("SQLite (paper_trading) 初期化完了")

    logger.info("すべての DB 初期化が完了しました")


if __name__ == "__main__":
    main()
