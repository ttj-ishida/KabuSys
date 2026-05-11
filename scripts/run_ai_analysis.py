# scripts/run_ai_analysis.py
"""Night batch: AI分析 — ニュースセンチメント + 市場レジーム判定 (ai_analysis_job)。

Task Scheduler から 18:00 に起動される。
score_news() と score_regime() を順次実行する。
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime
from kabusys.config import Settings
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.utils.logging_setup import setup_logging

setup_logging(app_name="ai_analysis")
logger = logging.getLogger(__name__)

_JOB_NAME = "ai_analysis_job"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    settings = Settings()
    conn = duckdb.connect(str(settings.duckdb_path))
    target_date = date.today()
    api_key = getattr(settings, "openai_api_key", None)
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    try:
        try:
            n_news = score_news(conn, target_date, api_key=api_key)
            _updated_rows["ai_scores"] = n_news
            logger.info("score_news 完了: %d 件スコア (date=%s)", n_news, target_date)
        except Exception as exc:
            logger.exception("score_news が失敗しました")
            _errors.append(f"score_news: {exc}")
            _failed = True

        if not _failed:
            try:
                n_regime = score_regime(conn, target_date, api_key=api_key)
                _updated_rows["market_regime"] = n_regime
                logger.info("score_regime 完了: %d 件 (date=%s)", n_regime, target_date)
            except Exception as exc:
                logger.exception("score_regime が失敗しました")
                _errors.append(f"score_regime: {exc}")
                _failed = True
    finally:
        conn.close()

    finished_at = datetime.now(timezone.utc)
    try:
        write_job_result(
            JobRunResult(
                job_name=_JOB_NAME,
                status="failed" if _failed else "success",
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=(finished_at - started_at).total_seconds(),
                updated_rows=_updated_rows,
                warnings=[],
                errors=_errors,
            )
        )
    except Exception:
        logger.warning("JobRunResult の書き出しに失敗しました", exc_info=True)

    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
