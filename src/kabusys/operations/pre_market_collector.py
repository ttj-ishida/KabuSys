"""
Pre-Market データ収集モジュール。

DB クエリ・ファイル確認・Task Scheduler 確認を行い、
pre_market_report.build_report() に渡す値を収集する。
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_FRESHNESS_DAYS = 3  # 直近 3 営業日以内なら OK（週末・祝日のギャップを考慮）


@dataclass
class PreMarketData:
    """収集した各チェック項目の生データ。"""

    data_freshness_ok: bool
    signal_queue_pending: int
    position_count: int
    stop_flag_exists: bool
    task_scheduler_ready: bool


def check_data_freshness(conn: object, today: date) -> bool:
    """prices_daily の最終更新日が today から 3 日以内なら True。"""
    row = conn.execute("SELECT MAX(date) FROM prices_daily").fetchone()
    if row is None or row[0] is None:
        return False
    last_date = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
    return (today - last_date).days <= _FRESHNESS_DAYS


def check_signal_queue(conn: object, today: date) -> int:
    """本日の pending シグナル件数を返す。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE status = 'pending' AND date = ?",
        (today.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_position_count(conn: object) -> int:
    """positions テーブルの最新日のポジション銘柄数を返す。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM positions WHERE date = (SELECT MAX(date) FROM positions)"
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_stop_flag(stop_flag_path: Path) -> bool:
    """停止フラグファイルが存在すれば True。"""
    return stop_flag_path.exists()


def check_task_scheduler(task_name: str) -> bool:
    """Windows Task Scheduler で task_name の状態が Ready なら True。

    schtasks が利用できない環境（Linux CI 等）では False を返す。
    """
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name, "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning("schtasks 実行失敗: %s", e)
        return False

    if result.returncode != 0:
        logger.warning("schtasks 戻り値 %d: %s", result.returncode, result.stdout)
        return False

    # CSV 出力の 3 列目がステータス（例: "Ready", "Disabled", "Running"）
    for line in result.stdout.splitlines():
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 3 and "Ready" in parts[2]:
            return True
    return False


def collect(
    *,
    duckdb_conn: object,
    sqlite_conn: object,
    stop_flag_path: Path,
    task_name: str = "KabuSys_ExecutionStart",
    today: date | None = None,
) -> PreMarketData:
    """全チェック項目を収集して PreMarketData を返す。"""
    today = today or date.today()
    return PreMarketData(
        data_freshness_ok=check_data_freshness(duckdb_conn, today),
        signal_queue_pending=check_signal_queue(sqlite_conn, today),
        position_count=check_position_count(sqlite_conn),
        stop_flag_exists=check_stop_flag(stop_flag_path),
        task_scheduler_ready=check_task_scheduler(task_name),
    )
