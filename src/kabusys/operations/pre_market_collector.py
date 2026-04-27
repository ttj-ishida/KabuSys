"""
Pre-Market データ収集モジュール。

DB クエリ・ファイル確認・Task Scheduler 確認を行い、
pre_market_report.build_report() に渡す値を収集する。
"""

from __future__ import annotations

import csv
import logging
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
from pathlib import Path

logger = logging.getLogger(__name__)

_FRESHNESS_DAYS = 3  # today との差が 3 日以内なら OK（週末・祝日のギャップを考慮）


def _to_date(v: object) -> date | None:
    """DB から返る値を date に正規化する。datetime/str（スペース・T 区切り）も受け付ける。"""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    # ISO 8601 の datetime 文字列（"YYYY-MM-DD HH:MM:SS" / "YYYY-MM-DDTHH:MM:SS"）から
    # 日付部分（先頭 10 文字 "YYYY-MM-DD"）を取り出す
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        logger.warning("Unexpected date value from prices_daily: %r", v)
        return None


@dataclass
class PreMarketData:
    """収集した各チェック項目の生データ。"""

    data_freshness_ok: bool
    signal_queue_pending: int
    position_count: int
    stop_flag_exists: bool
    task_scheduler_ready: bool


def check_data_freshness(conn: object, today: date) -> bool:
    """prices_daily の最終更新日と today の差が 3 日以内なら True。

    DuckDB/SQLite ドライバの設定によって MAX(date) が datetime や str で
    返ることがあるため、_to_date() で正規化してから比較する。
    未来日（last_date > today）は 0 日差とみなさず False 扱いにする。
    """
    row = conn.execute("SELECT MAX(date) FROM prices_daily").fetchone()
    last_date = _to_date(row[0] if row else None)
    if last_date is None:
        return False
    if last_date > today:
        return False
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
        logger.warning(
            "schtasks 戻り値 %d: stdout=%s stderr=%s",
            result.returncode,
            result.stdout,
            result.stderr,
        )
        return False

    # CSV 出力の 3 列目がステータス（例: "Ready", "Disabled", "Running"）
    # csv.reader を使い引用符内カンマを正しく処理する。
    # 日本語 OS では "準備完了" が返る場合があるため、受理語彙セットで判定する。
    _READY_STATUSES = {"ready", "準備完了"}
    for row in csv.reader(StringIO(result.stdout)):
        if len(row) >= 3 and row[2].strip().lower() in _READY_STATUSES:
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
