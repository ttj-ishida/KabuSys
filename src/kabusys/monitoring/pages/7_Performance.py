"""pages/7_Performance.py — 運用成績・ポジション・取引履歴・Paper Verification ビュー。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_open_positions,
    load_portfolio_performance,
    load_recent_trades,
)
from kabusys.monitoring.operations_data import load_paper_verification_data

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
    tab_perf, tab_pos, tab_trades, tab_paper = st.tabs(
        ["エクイティカーブ", "ポジション", "取引履歴", "Paper Verification"]
    )

    with tab_perf:
        df = load_portfolio_performance(conn, env=settings.env, days=days)
        if df.empty:
            st.info("パフォーマンスデータがありません。")
        else:
            latest = df.iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Equity", f"¥{float(latest['equity']):,.0f}")
            col2.metric("Cash", f"¥{float(latest['cash']):,.0f}")
            dd_val = latest.get("drawdown")
            dd = 0.0 if pd.isna(dd_val) else float(dd_val) * 100
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
            total_mv = float(
                pd.to_numeric(df["market_value"], errors="coerce").fillna(0).sum()
            )
            st.metric("時価総額合計", f"¥{total_mv:,.0f}")
            st.dataframe(df, use_container_width=True)

    with tab_trades:
        st.subheader("直近50件の取引履歴")
        df = load_recent_trades(conn)
        if df.empty:
            st.info("取引履歴がありません。")
        else:
            st.dataframe(df, use_container_width=True)

    with tab_paper:
        st.subheader("Paper Verification")
        if settings.env != "paper_trading":
            st.info(
                "📋 Paper Verification は `KABUSYS_ENV=paper_trading` 環境でのみ表示されます。"
            )
        else:
            col_from, col_to = st.columns(2)
            with col_from:
                from_date = st.date_input(
                    "開始日", value=date.today() - timedelta(days=30)
                )
            with col_to:
                to_date = st.date_input("終了日", value=date.today())

            from_dt = f"{from_date}T00:00:00+00:00"
            to_dt = f"{to_date}T23:59:59.999999+00:00"

            paper_path = Path(str(settings.paper_sqlite_path))
            data = load_paper_verification_data(
                paper_path, from_dt=from_dt, to_dt=to_dt
            )

            if not data.get("available"):
                st.warning(
                    f"Paper Trading DB が見つかりません: {paper_path}\n"
                    "Paper Trading を起動して実行してください。"
                )
            else:
                if data["pass_fail"] == "PASS":
                    st.success("✅ PASS — すべての閾値をクリア")
                else:
                    st.error("❌ FAIL — 一部の指標が閾値未達")

                col1, col2, col3, col4 = st.columns(4)
                uptime = data["uptime_pct"]
                fill = data["fill_rate_pct"]
                send = data["send_rate_pct"]
                p95 = data["p95_latency_ms"]

                col1.metric(
                    "稼働率",
                    f"{uptime:.1f}%" if uptime is not None else "N/A",
                    help="閾値: ≥99%",
                )
                col2.metric(
                    "約定率",
                    f"{fill:.1f}%" if fill is not None else "N/A",
                    help="閾値: ≥90%",
                )
                col3.metric(
                    "送信率",
                    f"{send:.1f}%" if send is not None else "N/A",
                    help="閾値: ≥95%",
                )
                col4.metric(
                    "P95 レイテンシ",
                    f"{p95:.0f} ms" if p95 is not None else "N/A",
                    help="閾値: ≤200ms",
                )

                st.caption(
                    f"集計対象: {from_date} ～ {to_date} / "
                    f"総ポーリング数: {data['total_polls']} / "
                    f"注文数: {data['created_count']}"
                )
finally:
    conn.close()
