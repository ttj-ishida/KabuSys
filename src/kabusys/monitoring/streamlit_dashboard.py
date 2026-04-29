"""streamlit_dashboard.py — KabuSys 監視ダッシュボード。

起動方法:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from datetime import datetime, timedelta, timezone
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


def load_recent_risk_logs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM risk_logs ORDER BY logged_at DESC LIMIT ?", (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]


def main(db_path: str) -> None:
    st.set_page_config(page_title="KabuSys Monitor", layout="wide")
    st.title("KabuSys 監視ダッシュボード")

    settings = Settings()

    with st.sidebar:
        if st.button("Refresh"):
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
            kill_active, kill_reason = check_kill_switch(Path(settings.kill_flag_path))
            if kill_active:
                st.error(f"🚫 Kill Switch 発動中: {kill_reason}")
            else:
                st.success("✅ Kill Switch: 発動なし")

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

                cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                conn.row_factory = sqlite3.Row
                order_error_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM risk_logs WHERE event_type='ORDER_ERROR' AND logged_at > ?",
                    (cutoff,),
                ).fetchone()["cnt"]
                stale_order_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM risk_logs WHERE event_type='STALE_ORDER' AND logged_at > ?",
                    (cutoff,),
                ).fetchone()["cnt"]

                col4, col5 = st.columns(2)
                col4.metric("注文エラー（直近1時間）", order_error_count)
                col5.metric("滞留注文（直近1時間）", stale_order_count)
            else:
                st.info("No dashboard data yet.")

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
            exec_ok = check_pid_file(Path(settings.pid_file_path))
            mon_ok = check_pid_file(_MONITORING_PID)
            pid_col1, pid_col2 = st.columns(2)
            pid_col1.metric("Execution", "OK" if exec_ok else "DOWN")
            pid_col2.metric("Monitoring", "OK" if mon_ok else "DOWN")

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

            risk_logs = load_recent_risk_logs(conn)
            if risk_logs:
                st.subheader("Recent Risk Events")
                st.dataframe(risk_logs, use_container_width=True)

        time.sleep(refresh_interval)
        st.rerun()
    finally:
        conn.close()


if __name__ == "__main__":
    main(_get_db_path())
