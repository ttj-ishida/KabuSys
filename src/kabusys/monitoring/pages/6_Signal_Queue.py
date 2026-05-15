"""pages/6_Signal_Queue.py — 翌営業日の発注予定・シグナル確認ビュー（参照専用）。"""

from __future__ import annotations

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.dashboard_data import (
    load_portfolio_targets,
    load_signal_queue,
    load_signals,
)

_KNOWN_STATUSES = ["pending", "processing", "filled", "cancelled", "error", "failed"]

st.set_page_config(page_title="Signal Queue", layout="wide", page_icon="📋")
st.title("📋 Signal Queue — 発注予定・シグナル確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

# ---------------------------------------------------------------------------
# 表示フェーズ（read_only=True — CLI の書き込みをブロックしない）
# ---------------------------------------------------------------------------
try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    if "File is already open" in str(e) or "Cannot open file" in str(e):
        st.warning(
            "⚙️ バッチまたは執行エンジンが DB を使用中のため、データを一時的に表示できません。"
            "しばらく待ってから **🔄 Refresh** してください。"
        )
    else:
        st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_queue, tab_targets, tab_signals = st.tabs(
        ["発注キュー", "ポートフォリオ目標", "シグナル（直近7日）"]
    )

    with tab_queue:
        st.subheader("Signal Queue（全件）")

        df = load_signal_queue(conn)
        pending = df[df["status"] == "pending"] if not df.empty else df.iloc[0:0]

        # ステータスフィルター — 実データと既知ステータスのユニオンでオプションを構築
        actual_statuses = sorted(df["status"].dropna().unique().tolist()) if not df.empty else []
        all_options = sorted(set(_KNOWN_STATUSES) | set(actual_statuses))
        default_statuses = [s for s in all_options if s != "cancelled"]
        selected_statuses = st.multiselect(
            "表示するステータス",
            options=all_options,
            default=default_statuses,
            help="cancelled はデフォルトで非表示。チェックを入れると表示されます。全解除すると0件表示になります。",
        )

        if df.empty:
            st.info("発注キューにシグナルはありません。")
        else:
            st.metric("pending 件数（全体）", len(pending))
            filtered_df = df[df["status"].isin(selected_statuses)]
            st.dataframe(filtered_df, use_container_width=True)

        # --- キャンセル操作（CLIコマンド案内）---
        st.divider()
        st.subheader("Pending シグナルのキャンセル")
        st.info(
            "このページは参照専用です。ステータス変更は **CLI** で実行してください。"
            "以下のコマンドをターミナルにコピーして実行します。"
        )

        if df.empty or pending.empty:
            st.caption("キャンセル可能な pending シグナルはありません。")
        else:
            pending_dates = sorted(pending["date"].astype(str).unique().tolist())

            for d in pending_dates:
                n = len(pending[pending["date"].astype(str) == d])
                st.caption(f"**{d}（{n} 件）をキャンセル:**")
                st.code(
                    f"python scripts/cancel_signal_queue.py --date {d}",
                    language="bash",
                )

            st.caption("**全 pending をキャンセル（日付問わず）:**")
            st.code("python scripts/cancel_signal_queue.py --all", language="bash")

            st.caption("**銘柄コードで絞り込む場合**（`--date` と組み合わせ）:")
            st.code(
                f"python scripts/cancel_signal_queue.py --date {pending_dates[0]} --code <銘柄コード>",
                language="bash",
            )

        # --- cancelled 物理削除（CLIコマンド案内）---
        st.divider()
        st.subheader("Cancelled レコードの削除")
        st.info("このページは参照専用です。レコードの削除は **CLI** で実行してください。")

        cancelled_count = len(df[df["status"] == "cancelled"]) if not df.empty else 0

        if cancelled_count == 0:
            st.caption("削除可能な cancelled レコードはありません。")
        else:
            st.caption(f"cancelled レコード: {cancelled_count} 件")
            st.code(
                "python scripts/cancel_signal_queue.py --delete-cancelled",
                language="bash",
            )

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
