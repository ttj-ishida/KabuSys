"""intraday_collector.py — ザラ場中監視用 DB 読み取りコレクター（純粋関数）。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

import psutil

from kabusys.config import Settings

_MONITORING_PID = Path(__file__).resolve().parents[3] / "data" / "monitoring.pid"


@dataclass
class IntradaySnapshot:
    collected_at: str
    execution_pid_ok: bool
    monitoring_pid_ok: bool
    kill_switch_active: bool
    kill_switch_reason: str
    drawdown_pct: float | None
    stale_order_count: int
    order_error_count: int
    process_ok: bool
    cpu_percent: float | None
    memory_percent: float | None
    recent_risk_events: list[dict] = field(default_factory=list)


def check_pid_file(pid_path: Path) -> bool:
    """PID ファイルが存在し、記録された PID が psutil で生存していれば True。"""
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
        return psutil.pid_exists(pid)
    except (ValueError, OSError):
        return False


def check_kill_switch(flag_path: Path) -> tuple[bool, str]:
    """(active, reason) を返す。flag がなければ (False, "")。"""
    if not flag_path.exists():
        return False, ""
    try:
        reason = flag_path.read_text().strip()
    except OSError:
        reason = ""
    return True, reason


def get_dashboard_row(conn: sqlite3.Connection) -> dict | None:
    """dashboard テーブルの最新行を dict で返す。レコードなしなら None。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM dashboard ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None


def count_recent_risk_events(
    conn: sqlite3.Connection, event_type: str, minutes: int = 60
) -> int:
    """指定 event_type の直近 N 分以内の件数を返す。"""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    conn.row_factory = None
    cursor = conn.execute(
        "SELECT COUNT(*) FROM risk_logs WHERE event_type = ? AND logged_at > ?",
        (event_type, cutoff),
    )
    return cursor.fetchone()[0]


def get_latest_system_status(conn: sqlite3.Connection) -> dict | None:
    """system_status の最新1件を dict で返す。レコードなしなら None。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM system_status ORDER BY recorded_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_recent_risk_events(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """risk_logs を logged_at DESC で最新 limit 件返す。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM risk_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def collect_intraday_snapshot(
    conn: sqlite3.Connection, settings: Settings
) -> IntradaySnapshot:
    """全チェック関数を呼び出して IntradaySnapshot を返す。"""
    now = datetime.now(timezone.utc).isoformat()

    execution_pid_ok = check_pid_file(Path(settings.pid_file_path))
    monitoring_pid_ok = check_pid_file(_MONITORING_PID)
    kill_switch_active, kill_switch_reason = check_kill_switch(
        Path(settings.kill_flag_path)
    )

    dashboard = get_dashboard_row(conn)
    drawdown_pct = dashboard["drawdown_pct"] if dashboard else None

    stale_order_count = count_recent_risk_events(conn, "STALE_ORDER")
    order_error_count = count_recent_risk_events(conn, "ORDER_ERROR")

    sys_status = get_latest_system_status(conn)
    process_ok = bool(sys_status["process_ok"]) if sys_status else False
    cpu_percent = sys_status["cpu_percent"] if sys_status else None
    memory_percent = sys_status["memory_percent"] if sys_status else None

    recent_risk_events = get_recent_risk_events(conn)

    return IntradaySnapshot(
        collected_at=now,
        execution_pid_ok=execution_pid_ok,
        monitoring_pid_ok=monitoring_pid_ok,
        kill_switch_active=kill_switch_active,
        kill_switch_reason=kill_switch_reason,
        drawdown_pct=drawdown_pct,
        stale_order_count=stale_order_count,
        order_error_count=order_error_count,
        process_ok=process_ok,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        recent_risk_events=recent_risk_events,
    )
