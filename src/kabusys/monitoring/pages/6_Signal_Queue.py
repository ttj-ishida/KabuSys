"""pages/6_Signal_Queue.py — 翌営業日の発注予定・シグナル確認ビュー。"""

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

        # --- キャンセル操作 ---
        st.divider()
        st.subheader("Pending シグナルのキャンセル")

        if df.empty or pending.empty:
            st.info("キャンセル可能な pending シグナルはありません。")
        else:
            pending_ids = pending["signal_id"].tolist()

            # 個別選択キャンセル
            selected = st.multiselect(
                "キャンセルするシグナルを選択（signal_id）",
                options=pending_ids,
                help="pending ステータスのシグナルのみ表示されます",
            )

            col_sel, col_all = st.columns(2)

            with col_sel:
                if st.button(
                    f"選択した {len(selected)} 件をキャンセル",
                    disabled=len(selected) == 0,
                    type="primary",
                ):
                    st.session_state["cancel_targets"] = selected
                    st.session_state["cancel_mode"] = "selected"

            with col_all:
                if st.button(
                    f"全 pending（{len(pending_ids)} 件）をキャンセル",
                    type="secondary",
                ):
                    st.session_state["cancel_targets"] = pending_ids
                    st.session_state["cancel_mode"] = "all"

            # 確認ダイアログ
            if "cancel_targets" in st.session_state:
                targets = st.session_state["cancel_targets"]
                mode_label = (
                    f"選択した {len(targets)} 件"
                    if st.session_state.get("cancel_mode") == "selected"
                    else f"全 pending {len(targets)} 件"
                )
                st.warning(f"{mode_label} を `cancelled` に変更します。この操作は元に戻せません。")
                confirm_col, abort_col = st.columns(2)
                with confirm_col:
                    if st.button("確定してキャンセル実行", type="primary"):
                        try:
                            write_conn = duckdb.connect(str(settings.duckdb_path))
                            placeholders = ", ".join(["?" for _ in targets])
                            updated = write_conn.execute(
                                f"UPDATE signal_queue SET status = 'cancelled'"
                                f" WHERE signal_id IN ({placeholders})"
                                f" AND status = 'pending'"
                                f" RETURNING signal_id",
                                targets,
                            ).fetchall()
                            write_conn.close()
                            count = len(updated)
                            st.success(f"{count} 件を cancelled に変更しました。")
                            del st.session_state["cancel_targets"]
                            del st.session_state["cancel_mode"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"キャンセル処理に失敗しました: {e}")
                with abort_col:
                    if st.button("戻る"):
                        del st.session_state["cancel_targets"]
                        del st.session_state["cancel_mode"]
                        st.rerun()

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
