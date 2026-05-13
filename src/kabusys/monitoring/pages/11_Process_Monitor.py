"""pages/11_Process_Monitor.py — プロセス実行状況監視ページ。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import MonitoringDB
from kabusys.operations.process_registry import is_pid_alive
from kabusys.utils.datetime_utils import to_jst_str

st.set_page_config(page_title="Process Monitor", layout="wide", page_icon="🖥️")
st.title("🖥️ Process Monitor — プロセス実行状況")

settings = Settings()

with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    hours = st.selectbox("取得範囲（時間）", [12, 24, 48, 72], index=1)
    if st.button("🔄 更新"):
        st.rerun()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
except sqlite3.OperationalError:
    st.error(f"Database not found: {settings.sqlite_path}")
    st.stop()

try:
    db = MonitoringDB(conn)
    rows = db.list_recent_processes(hours=hours)
finally:
    conn.close()

running = [r for r in rows if r["finished_at"] is None]
completed = [r for r in rows if r["finished_at"] is not None]

alive_running = []
orphaned = []
for r in running:
    pid = r.get("pid")
    if pid is not None and not is_pid_alive(pid):
        orphaned.append(r)
    else:
        alive_running.append(r)


def _elapsed(started_at_iso: str, finished_at_iso: str | None = None) -> str:
    try:
        start = datetime.fromisoformat(started_at_iso)
        end = (
            datetime.fromisoformat(finished_at_iso)
            if finished_at_iso
            else datetime.now(timezone.utc)
        )
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        secs = int((end - start).total_seconds())
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        if h:
            return f"{h}h{m:02d}m{s:02d}s"
        elif m:
            return f"{m}m{s:02d}s"
        return f"{s}s"
    except Exception:
        return "?"


# --- 実行中プロセス ---
st.subheader("実行中プロセス")
if alive_running:
    st.dataframe(
        [
            {
                "ジョブ名": r["job_name"],
                "PID": r["pid"] or "-",
                "開始": to_jst_str(r["started_at"]),
                "経過": _elapsed(r["started_at"]),
                "ログ": r.get("log_file") or "",
            }
            for r in alive_running
        ],
        use_container_width=True,
    )
else:
    st.info("実行中プロセスはありません。")

# --- 孤立プロセス（クラッシュ検知） ---
if orphaned:
    st.subheader("⚠️ 孤立プロセス（クラッシュ検知）")
    st.warning(f"{len(orphaned)} 件の孤立プロセスが検出されました（PID 生存なし）。")
    st.dataframe(
        [
            {
                "ジョブ名": r["job_name"],
                "PID": r["pid"] or "-",
                "開始": to_jst_str(r["started_at"]),
                "経過": _elapsed(r["started_at"]),
                "ログ": r.get("log_file") or "",
            }
            for r in orphaned
        ],
        use_container_width=True,
    )

# --- 直近の完了プロセス ---
st.subheader(f"直近の完了プロセス（過去 {hours} 時間）")
if completed:
    _STATUS_BADGE = {"success": "✅ success", "warning": "⚠️ warning", "failed": "❌ failed"}
    st.dataframe(
        [
            {
                "ジョブ名": r["job_name"],
                "ステータス": _STATUS_BADGE.get(r["status"], f"❓ {r['status']}"),
                "開始": to_jst_str(r["started_at"]),
                "終了": to_jst_str(r["finished_at"]) if r["finished_at"] else "N/A",
                "経過": _elapsed(r["started_at"], r["finished_at"]),
                "エラー": r.get("error_msg") or "",
            }
            for r in completed
        ],
        use_container_width=True,
    )
else:
    st.info(f"過去 {hours} 時間に完了したプロセスはありません。")
