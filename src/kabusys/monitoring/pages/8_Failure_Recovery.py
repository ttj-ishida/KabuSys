"""pages/8_Failure_Recovery.py — 障害対応集約ビュー。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_failure_summary
from kabusys.operations.intraday_collector import (
    _MONITORING_PID,
    check_kill_switch,
    check_pid_file,
)

st.set_page_config(page_title="Failure Recovery", layout="wide", page_icon="🚨")
st.title("🚨 Failure Recovery — 障害対応")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
except sqlite3.OperationalError:
    st.error(
        f"Database not found: {settings.sqlite_path}. Start MonitoringEngine first."
    )
    st.stop()

try:
    kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
    exec_ok = check_pid_file(Path(settings.pid_file_path))
    mon_ok = check_pid_file(_MONITORING_PID)

    if kill_active:
        st.error(f"🚫 Kill Switch 発動中: {kill_reason}")
    else:
        st.success("✅ Kill Switch: 発動なし")

    col1, col2 = st.columns(2)
    col1.metric("Execution Engine", "🟢 UP" if exec_ok else "🔴 DOWN")
    col2.metric("Monitoring", "🟢 UP" if mon_ok else "🔴 DOWN")

    st.divider()

    summary = load_failure_summary(conn)
    col3, col4, col5, col6 = st.columns(4)
    col3.metric("CRITICAL（直近24h）", summary["critical_count"])
    col4.metric("KILL_SWITCH（直近24h）", summary["kill_switch_count"])
    col5.metric("RISK_BREACH（直近24h）", summary["risk_breach_count"])
    col6.metric("ORDER_ERROR（直近24h）", summary["order_error_count"])

    st.subheader("直近イベント（直近24時間）")
    events = summary["recent_events"]
    if events:
        st.dataframe(events, use_container_width=True)
    else:
        st.success("直近24時間の障害イベントはありません。")

    st.divider()
    st.subheader("🔗 復旧手順ガイド")
    st.markdown("""
| 状況 | 参照先 |
|------|--------|
| Kill Switch が発動した | WebManual → Failure Recovery を参照 |
| 注文エラーが多い | `documents/08_Operations/TradingRunbook.md` を参照 |
| ポジション差分あり | Execution Startup ページで詳細確認 → `python -m kabusys.run_position_reconciliation_report` |
| データ更新失敗 | Pre-Market ページでデータ鮮度確認 → `python scripts/run_data_update.py` |
""")

finally:
    conn.close()
