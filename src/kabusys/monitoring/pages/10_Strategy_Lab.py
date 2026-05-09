"""pages/10_Strategy_Lab.py — 市場レジーム・AI スコア・戦略状態ビュー。"""

from __future__ import annotations

import sqlite3

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.components.ai_wizard import render as render_wizard
from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.monitoring.strategy_lab_data import (
    load_ai_scores,
    load_market_regime,
    load_signal_summary,
)

st.set_page_config(page_title="Strategy Lab", layout="wide", page_icon="📊")
st.title("📊 Strategy Lab — 市場レジーム・AI スコア")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    days = st.selectbox("表示期間", [14, 30, 60], index=1)
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_regime, tab_ai, tab_signals, tab_copilot = st.tabs(
        ["市場レジーム", "AI スコア", "シグナル推移", "🤖 AI Co-Pilot"]
    )

    with tab_regime:
        df = load_market_regime(conn, days=days)
        if df.empty:
            st.info("レジームデータがありません。")
        else:
            latest = df.iloc[-1]
            col1, col2 = st.columns(2)
            col1.metric("最新レジームスコア", f"{float(latest['regime_score']):.3f}")
            col2.metric("レジームラベル", latest["regime_label"])
            st.subheader("レジームスコア推移")
            st.line_chart(df.set_index("date")["regime_score"])
            st.dataframe(df, use_container_width=True)

    with tab_ai:
        df = load_ai_scores(conn)
        if df.empty:
            st.info(
                "AI スコアデータがありません（ENABLE_AI_SENTIMENT=false の場合は空）。"
            )
        else:
            st.caption(f"基準日: {df['date'].iloc[0]}")
            col1, col2 = st.columns(2)
            col1.metric("スコア最高銘柄", df.iloc[0]["code"])
            col2.metric("最高 AI スコア", f"{float(df.iloc[0]['ai_score']):.3f}")
            st.dataframe(df, use_container_width=True)

    with tab_signals:
        df = load_signal_summary(conn, days=days)
        if df.empty:
            st.info("シグナルデータがありません。")
        else:
            total_buy = int(df["buy_count"].sum())
            total_sell = int(df["sell_count"].sum())
            col1, col2 = st.columns(2)
            col1.metric(f"買いシグナル合計（{days}日）", total_buy)
            col2.metric(f"売りシグナル合計（{days}日）", total_sell)
            st.subheader("日別シグナル件数")
            st.bar_chart(df.set_index("date")[["buy_count", "sell_count"]])

    with tab_copilot:
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
        try:
            init_monitoring_db(sqlite_conn)
            render_wizard(conn, sqlite_conn)
        finally:
            sqlite_conn.close()
finally:
    conn.close()
