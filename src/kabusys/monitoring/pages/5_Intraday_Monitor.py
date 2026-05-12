"""pages/5_Intraday_Monitor.py — ザラ場監視ページ（自動更新付き）。"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_intraday_summary
from kabusys.operations.intraday_collector import (
    _MONITORING_PID,
    check_kill_switch,
    check_pid_file,
)

st.set_page_config(page_title="Intraday Monitor", layout="wide", page_icon="📡")
st.title("📡 Intraday Monitor — ザラ場監視")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    refresh_interval = st.selectbox("自動更新間隔（秒）", [30, 60, 120], index=0)
    if st.button("🔄 今すぐ更新"):
        st.rerun()

# Connect to SQLite (read-only URI mode)
try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
except sqlite3.OperationalError:
    st.error(
        f"Database not found or cannot open: {settings.sqlite_path}. Start MonitoringEngine first."
    )
    st.stop()

try:
    # Top status row: Kill Switch | Execution | Monitoring
    kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
    exec_ok = check_pid_file(Path(settings.pid_file_path))
    mon_ok = check_pid_file(_MONITORING_PID)

    col_k, col_e, col_m = st.columns(3)
    if kill_active:
        col_k.error(f"🚫 Kill Switch: {kill_reason}")
    else:
        col_k.success("✅ Kill Switch: 発動なし")
    col_e.metric("Execution Engine", "🟢 UP" if exec_ok else "🔴 DOWN")
    col_m.metric("Monitoring", "🟢 UP" if mon_ok else "🔴 DOWN")

    st.divider()

    # Metrics
    summary = load_intraday_summary(conn, hours=1)
    col1, col2, col3 = st.columns(3)
    dd = summary["drawdown_pct"]
    col1.metric("ドローダウン", f"{dd:.2f}%", delta_color="inverse")
    col2.metric("注文エラー（直近1h）", summary["order_errors"])
    col3.metric("滞留注文（直近1h）", summary["stale_orders"])

    if dd <= -10.0:
        st.warning(f"⚠️ ドローダウン {dd:.2f}% — 閾値 -10% 超過")

    st.divider()

    # Tabs
    tab_risk, tab_trade = st.tabs(["Risk Logs", "Trade Logs"])

    with tab_risk:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_type, metric_name, metric_value, threshold, detail, logged_at FROM risk_logs ORDER BY logged_at DESC LIMIT 50"
        ).fetchall()
        if rows:
            st.dataframe([dict(r) for r in rows], use_container_width=True)
        else:
            st.success("リスクイベントはありません。")
        conn.row_factory = None

    with tab_trade:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_type, client_order_id, code, side, qty, price, filled_qty, state, logged_at FROM trade_logs ORDER BY logged_at DESC LIMIT 50"
        ).fetchall()
        if rows:
            st.dataframe([dict(r) for r in rows], use_container_width=True)
        else:
            st.info("取引ログはありません。")
        conn.row_factory = None

    # Auto-refresh
    time.sleep(refresh_interval)
    st.rerun()

finally:
    conn.close()
