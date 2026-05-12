# scripts/run_yahoonews_collection.py
"""Night batch: Yahoo News RSS 収集 (yahoonews_collection_job)。

Task Scheduler から 15:33 に起動される。
ENABLE_YAHOONEWS=false（デフォルト）のときはスキップして正常終了する。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.data.news_collector import run_news_collection
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

setup_logging(app_name="yahoonews_collection")
logger = logging.getLogger(__name__)

_APP_NAME = "yahoonews_collection"


def _fetch_known_codes(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """stocks テーブルから上場銘柄コードを取得する。"""
    try:
        rows = conn.execute("SELECT DISTINCT code FROM stocks").fetchall()
        return [str(r[0]) for r in rows]
    except Exception:
        logger.warning(
            "stocks テーブルからの銘柄コード取得に失敗しました。symbol リンクをスキップします。",
            exc_info=True,
        )
        return []


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    settings = Settings()
    if not settings.enable_yahoonews:
        logger.info(
            "Yahoo News 収集はオプション機能です（ENABLE_YAHOONEWS=false）。スキップします。"
        )
        log_run_end(_APP_NAME, status="success", started_at=started_at)
        return
    conn = None
    _failed = False
    try:
        conn = duckdb.connect(str(settings.duckdb_path))
        known_codes = _fetch_known_codes(conn)
        saved = run_news_collection(
            conn,
            known_codes=known_codes if known_codes else None,
        )
        logger.info("yahoonews_collection 完了: saved=%d", saved)
    except Exception:
        logger.exception("yahoonews_collection バッチが失敗しました")
        _failed = True
    finally:
        if conn is not None:
            conn.close()
    log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
