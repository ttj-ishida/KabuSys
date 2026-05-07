"""streamlit_dashboard.py — KabuSys 監視ダッシュボード（Home ページ）。

マルチページ構成のエントリーポイント。pages/ 配下のページが自動的にサイドバーに表示される。

起動方法:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.monitoring_db import MonitoringDB
from kabusys.operations.intraday_collector import (
    _MONITORING_PID,
    check_kill_switch,
    check_pid_file,
)


def _get_db_path() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/monitoring.db")
    args, _ = parser.parse_known_args()
    return args.db


def load_positions(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM positions WHERE qty != 0 ORDER BY updated_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def load_recent_orders(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM trade_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def load_latest_system_status(conn: sqlite3.Connection) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM system_status ORDER BY recorded_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def main(db_path: str) -> None:
    st.set_page_config(page_title="KabuSys Monitor", layout="wide", page_icon="🏠")
    st.title("🏠 KabuSys 監視ダッシュボード — Home")

    settings = Settings()

    with st.sidebar:
        st.caption(f"環境: **{settings.env}**")
        if st.button("🔄 Refresh"):
            st.rerun()
        refresh_interval = st.selectbox("自動更新間隔", [30, 60, 120], index=0)
        st.caption(f"{refresh_interval}秒ごとに自動更新")

    try:
        uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        st.error(
            f"Database not found or cannot open (read-only): {db_path}. Start MonitoringEngine first."
        )
        return
    db = MonitoringDB(conn)

    try:
        tab_overview, tab_positions, tab_orders, tab_system = st.tabs(
            ["Overview", "Positions", "Orders", "System"]
        )

        with tab_overview:
            # --- システム状態サマリ ---
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

            dashboard = db.get_dashboard()
            if dashboard:
                col1, col2, col3 = st.columns(3)
                col1.metric("Portfolio Value", f"¥{dashboard['portfolio_value']:,.0f}")
                col2.metric("Cash", f"¥{dashboard['cash']:,.0f}")
                dd = dashboard["drawdown_pct"] * 100
                col3.metric("Drawdown", f"{dd:.2f}%", delta_color="inverse")
                if dd <= -10.0:
                    st.warning(f"⚠️ ドローダウン {dd:.2f}% — 閾値 -10% 超過")
                st.caption(f"Updated: {dashboard['updated_at']}")

            else:
                st.info("No dashboard data yet.")

            st.info("📡 ザラ場監視の詳細は **Intraday Monitor** ページを確認してください。")

        with tab_positions:
            positions = load_positions(conn)
            if positions:
                st.dataframe(positions, use_container_width=True)
            else:
                st.info("No open positions.")

        with tab_orders:
            orders = load_recent_orders(conn)
            if orders:
                st.dataframe(orders, use_container_width=True)
            else:
                st.info("No trade events yet.")

        with tab_system:
            status = load_latest_system_status(conn)
            if status:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("CPU", f"{status['cpu_percent']:.1f}%")
                col2.metric("Memory", f"{status['memory_percent']:.1f}%")
                col3.metric("Disk", f"{status['disk_percent']:.1f}%")
                col4.metric("Process", "OK" if status["process_ok"] else "DOWN")
                st.caption(f"Recorded: {status['recorded_at']}")
            else:
                st.info("No system status yet.")

        time.sleep(refresh_interval)
        st.rerun()
    finally:
        conn.close()


if __name__ == "__main__":
    main(_get_db_path())
