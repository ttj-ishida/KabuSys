# scripts/run_ai_analysis.py
"""Night batch: AI分析 — ニュースセンチメント + 市場レジーム判定 (ai_analysis_job)。

Task Scheduler から 18:00 に起動される。
score_news() と score_regime() を順次実行する。
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()
    api_key = getattr(settings, "openai_api_key", None)

    try:
        try:
            n_news = score_news(conn, target_date, api_key=api_key)
            logger.info("score_news 完了: %d 件スコア (date=%s)", n_news, target_date)
        except Exception:
            logger.exception("score_news が失敗しました")
            sys.exit(1)

        try:
            n_regime = score_regime(conn, target_date, api_key=api_key)
            logger.info("score_regime 完了: %d 件 (date=%s)", n_regime, target_date)
        except Exception:
            logger.exception("score_regime が失敗しました")
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
