# scripts/run_strategy_signal.py
"""Night batch: 売買シグナル生成 (strategy_signal_job)。

Task Scheduler から 20:00 に起動される。
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from kabusys.config import Settings
from kabusys.execution.order_repository import init_position_entries_db
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
from kabusys.operations.job_run_recorder import write_job_result
from kabusys.operations.night_batch_report import JobRunResult
from kabusys.operations.process_registry import register_process, update_process
from kabusys.strategy.signal_generator import generate_signals
from kabusys.utils.logging_setup import log_run_end, log_run_start, setup_logging

_DD_STOP_PCT = 0.12        # ポートフォリオが peak 比 12% 以上下落したら BUY を停止
_DD_STOP_TIMEOUT_DAYS = 30  # 停止発動から 30 カレンダー日後に自動解除

_run_log = setup_logging(app_name="strategy_signal", capture_stdio=True)
logger = logging.getLogger(__name__)

_JOB_NAME = "strategy_signal_job"
_APP_NAME = "strategy_signal"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    log_run_start(_APP_NAME)
    run_id: int | None = None
    try:
        run_id = register_process(_JOB_NAME, log_file=str(_run_log) if _run_log else None)
    except Exception:
        logger.warning("process_registry 登録に失敗しました", exc_info=True)
    conn = None
    _failed = False
    _errors: list[str] = []
    _updated_rows: dict[str, int] = {}

    sqlite_conn = None
    try:
        settings = Settings()
        conn = duckdb.connect(str(settings.duckdb_path))
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path), timeout=30.0)
        sqlite_conn.row_factory = sqlite3.Row
        init_position_entries_db(sqlite_conn)
        init_monitoring_db(sqlite_conn)
        target_date = date.today()

        # --- ポートフォリオ DD 停止チェック ---
        mdb = MonitoringDB(sqlite_conn)
        dashboard = mdb.get_dashboard()
        entry_blocked = False
        if dashboard is not None:
            drawdown_pct = float(dashboard["drawdown_pct"])
            blocked_since_str = dashboard["dd_stop_blocked_since"]
            blocked_since = date.fromisoformat(blocked_since_str) if blocked_since_str else None

            # タイムアウト解除チェック
            if blocked_since is not None:
                elapsed = (target_date - blocked_since).days
                if elapsed >= _DD_STOP_TIMEOUT_DAYS:
                    logger.info(
                        "DD 停止タイムアウト解除: blocked_since=%s elapsed=%d日",
                        blocked_since_str,
                        elapsed,
                    )
                    mdb.upsert_dashboard(
                        portfolio_value=float(dashboard["portfolio_value"]),
                        cash=float(dashboard["cash"]),
                        drawdown_pct=drawdown_pct,
                        open_order_count=int(dashboard["open_order_count"]),
                        position_count=int(dashboard["position_count"]),
                        peak_value=float(dashboard["portfolio_value"]),  # ピークをリセット
                        clear_dd_stop=True,
                    )
                    blocked_since = None

            # DD 停止判定
            if blocked_since is None and drawdown_pct > _DD_STOP_PCT:
                entry_blocked = True
                mdb.upsert_dashboard(
                    portfolio_value=float(dashboard["portfolio_value"]),
                    cash=float(dashboard["cash"]),
                    drawdown_pct=drawdown_pct,
                    open_order_count=int(dashboard["open_order_count"]),
                    position_count=int(dashboard["position_count"]),
                    dd_stop_blocked_since=target_date.isoformat(),
                )
                logger.warning(
                    "DD 停止発動: drawdown=%.1f%% > %.0f%% → BUY シグナル生成をスキップ",
                    drawdown_pct * 100,
                    _DD_STOP_PCT * 100,
                )
            elif blocked_since is not None:
                entry_blocked = True
                logger.info(
                    "DD 停止継続中: blocked_since=%s drawdown=%.1f%%",
                    blocked_since_str,
                    drawdown_pct * 100,
                )

        n = generate_signals(
            conn,
            target_date,
            use_ma200_filter=True,
            adaptive_threshold_vol_regime=True,
            topix_vol_low_threshold=0.12,
            dynamic_trailing_stop=True,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            entry_blocked=entry_blocked,
            sqlite_conn=sqlite_conn,
        )
        _updated_rows["signals"] = n
        logger.info("シグナル生成完了: %d 件 (date=%s)", n, target_date)
    except Exception as exc:
        logger.exception("generate_signals が失敗しました")
        _errors.append(str(exc))
        _failed = True
    finally:
        if conn is not None:
            conn.close()
        if sqlite_conn is not None:
            sqlite_conn.close()

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
