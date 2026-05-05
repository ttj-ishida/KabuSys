"""pages/3_Performance.py — 運用成績・ポジション・取引履歴ビュー。"""

from __future__ import annotations

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_open_positions,
    load_portfolio_performance,
    load_recent_trades,
)

st.set_page_config(page_title="Performance", layout="wide", page_icon="📈")
st.title("📈 Performance — 運用成績")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    days = st.selectbox("表示期間", [30, 60, 90, 180], index=2)
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_perf, tab_pos, tab_trades = st.tabs(
        ["エクイティカーブ", "ポジション", "取引履歴"]
    )

    with tab_perf:
        df = load_portfolio_performance(conn, days=days)
        if df.empty:
            st.info("パフォーマンスデータがありません。")
        else:
            latest = df.iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Equity", f"¥{float(latest['equity']):,.0f}")
            col2.metric("Cash", f"¥{float(latest['cash']):,.0f}")
            dd = (
                float(latest["drawdown"]) * 100
                if latest["drawdown"] is not None
                else 0.0
            )
            col3.metric("Drawdown", f"{dd:.2f}%")

            st.subheader("エクイティカーブ")
            st.line_chart(df.set_index("date")["equity"])

            ret_df = df.set_index("date")["daily_return"].dropna()
            if not ret_df.empty:
                st.subheader("日次リターン (%)")
                st.bar_chart(ret_df * 100)

            dd_df = df.set_index("date")["drawdown"].dropna() * 100
            if not dd_df.empty:
                st.subheader("ドローダウン推移 (%)")
                st.line_chart(dd_df)

    with tab_pos:
        st.subheader("保有ポジション（最新日）")
        df = load_open_positions(conn)
        if df.empty:
            st.info("保有ポジションはありません。")
        else:
            st.caption(f"基準日: {df['date'].iloc[0]}")
            total_mv = float(df["market_value"].sum())
            st.metric("時価総額合計", f"¥{total_mv:,.0f}")
            st.dataframe(df, use_container_width=True)

    with tab_trades:
        st.subheader("直近50件の取引履歴")
        df = load_recent_trades(conn)
        if df.empty:
            st.info("取引履歴がありません。")
        else:
            st.dataframe(df, use_container_width=True)
finally:
    conn.close()
