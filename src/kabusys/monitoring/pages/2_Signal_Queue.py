"""pages/2_Signal_Queue.py — 翌営業日の発注予定・シグナル確認ビュー。"""

from __future__ import annotations

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_portfolio_targets,
    load_signal_queue,
    load_signals,
)

st.set_page_config(page_title="Signal Queue", layout="wide", page_icon="📋")
st.title("📋 Signal Queue — 発注予定・シグナル確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_queue, tab_targets, tab_signals = st.tabs(
        ["発注キュー", "ポートフォリオ目標", "シグナル（直近7日）"]
    )

    with tab_queue:
        st.subheader("Signal Queue（全件）")
        df = load_signal_queue(conn)
        if df.empty:
            st.info("発注キューにシグナルはありません。")
        else:
            pending = df[df["status"] == "pending"]
            st.metric("pending 件数", len(pending))
            st.dataframe(df, use_container_width=True)

    with tab_targets:
        st.subheader("ポートフォリオ目標（最新日）")
        df = load_portfolio_targets(conn)
        if df.empty:
            st.info("ポートフォリオ目標データがありません。")
        else:
            st.caption(f"基準日: {df['date'].iloc[0]}")
            st.dataframe(df, use_container_width=True)

    with tab_signals:
        st.subheader("生成シグナル（直近7日）")
        df = load_signals(conn)
        if df.empty:
            st.info("シグナルデータがありません。")
        else:
            col1, col2 = st.columns(2)
            col1.metric("買いシグナル", len(df[df["side"] == "buy"]))
            col2.metric("売りシグナル", len(df[df["side"] == "sell"]))
            st.dataframe(df, use_container_width=True)
finally:
    conn.close()
