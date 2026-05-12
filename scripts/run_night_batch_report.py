"""scripts/run_night_batch_report.py

夜間バッチ結果確認レポートの生成ランナー。

artifacts/job_runs/{date}/ から JobRunResult を読み込み、
DuckDB からカウントを取得してレポートを生成・保存する。
Task Scheduler または手動実行で使用する。
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.operations.job_run_recorder import read_job_results
from kabusys.operations.night_batch_report import (
    JobRunResult,
    NextDaySummary,
    UpdateCounts,
    build_report,
    format_cli_summary,
    save_report,
)
from kabusys.operations.process_registry import register_process, update_process
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_run_log = setup_logging(app_name="night_batch_report", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "night_batch_report_job"
_APP_NAME = "night_batch_report"


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def load_job_results_or_empty(
    run_date: date,
    base_dir: Path | None = None,
) -> list[JobRunResult]:
    """read_job_results を呼び出し、例外が発生した場合は空リストを返す。"""
    try:
        return read_job_results(run_date, base_dir=base_dir)
    except Exception:
        logger.warning(
            "JobRunResult の読み込みに失敗しました。空リストで続行します。",
            exc_info=True,
        )
        return []


def _count_table(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    run_date: date,
) -> int:
    """指定テーブルの run_date 行数を返す。テーブルが存在しない場合は 0 を返す。"""
    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE date = ?",  # noqa: S608
            [run_date],
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def collect_update_counts(
    conn: duckdb.DuckDBPyConnection,
    run_date: date,
) -> UpdateCounts:
    """DB から各テーブルの run_date 行数を取得して UpdateCounts を返す。

    存在しないテーブルへのクエリは 0 として扱う。
    """
    return UpdateCounts(
        prices_daily=_count_table(conn, "prices_daily", run_date),
        raw_news=_count_table(conn, "raw_news", run_date),
        fundamentals=_count_table(conn, "fundamentals", run_date),
        features=_count_table(conn, "features", run_date),
        ai_scores=_count_table(conn, "ai_scores", run_date),
        market_regime=_count_table(conn, "market_regime", run_date),
        signals=_count_table(conn, "signals", run_date),
        signal_queue=_count_table(conn, "signal_queue", run_date),
    )


def collect_next_day_summary(
    conn: duckdb.DuckDBPyConnection,
    run_date: date,
) -> NextDaySummary:
    """DB からシグナル情報を取得して NextDaySummary を返す。

    buy/sell カウントは signals テーブルから取得する。
    テーブルが存在しない場合は 0 として扱う。
    """
    buy_count = 0
    sell_count = 0
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'",
            [run_date],
        ).fetchone()
        buy_count = int(row[0]) if row else 0
    except Exception:
        pass

    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'sell'",
            [run_date],
        ).fetchone()
        sell_count = int(row[0]) if row else 0
    except Exception:
        pass

    return NextDaySummary(
        buy_count=buy_count,
        sell_count=sell_count,
    )


# ---------------------------------------------------------------------------
# CLI 引数パース
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="夜間バッチ結果確認レポートを生成する。",
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="DuckDB ファイルのパス（省略時は Settings().duckdb_path）",
    )
    parser.add_argument(
        "--date",
        metavar="DATE",
        default=None,
        help="実行日（YYYY-MM-DD 形式、省略時は今日）",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=None,
        help="レポート JSON の保存先ディレクトリ（省略時: artifacts/reports）",
    )
    parser.add_argument(
        "--job-runs-dir",
        metavar="DIR",
        default=None,
        help="ジョブ実行 JSON の読み込み元ディレクトリ（省略時: artifacts/job_runs）",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()  # argparse の --help / バリデーションエラーはマーカー出力前に終了
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    _failed = False
    try:
        if args.date:
            try:
                run_date = date.fromisoformat(args.date)
            except ValueError:
                logger.error("--date の形式が不正です: %s (YYYY-MM-DD が必要です)", args.date)
                _failed = True
        else:
            run_date = date.today()

        if not _failed:
            logger.info("レポート生成開始: run_date=%s", run_date)

            # --- JobRunResult 読み込み ---
            job_runs_base = Path(args.job_runs_dir) if args.job_runs_dir else None
            job_results = load_job_results_or_empty(run_date, base_dir=job_runs_base)
            logger.info("JobRunResult 読み込み: %d 件", len(job_results))

            # --- DB クエリ ---
            db_path = args.db or str(Settings().duckdb_path)
            target_date: date = run_date + timedelta(days=1)
            conn = duckdb.connect(db_path)
            update_counts = collect_update_counts(conn, run_date)
            next_day = collect_next_day_summary(conn, run_date)
            try:
                row = conn.execute(
                    "SELECT MIN(date) FROM prices_daily WHERE date > ?", [run_date]
                ).fetchone()
                if row and row[0]:
                    target_date = row[0]
            except Exception:
                logger.warning(
                    "翌営業日の取得に失敗しました。run_date+1 を使用します。", exc_info=True
                )

            # --- レポート構築・保存 ---
            report = build_report(
                job_results,
                update_counts,
                next_day,
                run_date=run_date,
                target_date=target_date,
            )

            output_dir = Path(args.output_dir) if args.output_dir else Path("artifacts/reports")
            saved_path = save_report(report, output_dir)
            logger.info("レポート保存: %s", saved_path)

            print(format_cli_summary(report))
    except Exception:
        logger.exception("night_batch_report バッチが失敗しました")
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        if run_id is not None:
            try:
                update_process(run_id, status="failed" if _failed else "success")
            except Exception:
                logger.warning("process_registry 更新に失敗しました", exc_info=True)
        log_run_end(_APP_NAME, status="failed" if _failed else "success", started_at=started_at)
    if _failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
