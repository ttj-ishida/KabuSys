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

_ALL_STATUSES = ["pending", "processing", "filled", "cancelled", "error", "failed"]
_DEFAULT_STATUSES = ["pending", "processing", "filled", "error", "failed"]  # cancelled を除外

st.set_page_config(page_title="Signal Queue", layout="wide", page_icon="📋")
st.title("📋 Signal Queue — 発注予定・シグナル確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path))
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_queue, tab_targets, tab_signals = st.tabs(
        ["発注キュー", "ポートフォリオ目標", "シグナル（直近7日）"]
    )

    with tab_queue:
        st.subheader("Signal Queue（全件）")

        # ステータスフィルター
        selected_statuses = st.multiselect(
            "表示するステータス",
            options=_ALL_STATUSES,
            default=_DEFAULT_STATUSES,
            help="cancelled はデフォルトで非表示。チェックを入れると表示されます。",
        )

        df = load_signal_queue(conn)
        if df.empty:
            st.info("発注キューにシグナルはありません。")
        else:
            pending = df[df["status"] == "pending"]
            st.metric("pending 件数", len(pending))
            filtered_df = df[df["status"].isin(selected_statuses)] if selected_statuses else df
            st.dataframe(filtered_df, use_container_width=True)

        # --- キャンセル操作 ---
        st.divider()
        st.subheader("Pending シグナルのキャンセル")

        if df.empty or pending.empty:
            st.info("キャンセル可能な pending シグナルはありません。")
        else:
            pending_ids = pending["signal_id"].tolist()

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
                    st.session_state["sq_cancel_targets"] = selected
                    st.session_state["sq_cancel_mode"] = "selected"

            with col_all:
                if st.button(
                    f"全 pending（{len(pending_ids)} 件）をキャンセル",
                    type="secondary",
                ):
                    st.session_state["sq_cancel_targets"] = pending_ids
                    st.session_state["sq_cancel_mode"] = "all"

            if "sq_cancel_targets" in st.session_state:
                targets = st.session_state["sq_cancel_targets"]
                mode_label = (
                    f"選択した {len(targets)} 件"
                    if st.session_state.get("sq_cancel_mode") == "selected"
                    else f"全 pending {len(targets)} 件"
                )
                st.warning(f"{mode_label} を `cancelled` に変更します。この操作は元に戻せません。")
                confirm_col, abort_col = st.columns(2)
                with confirm_col:
                    if st.button("確定してキャンセル実行", type="primary"):
                        try:
                            placeholders = ", ".join(["?" for _ in targets])
                            updated = conn.execute(
                                f"UPDATE signal_queue SET status = 'cancelled'"
                                f" WHERE signal_id IN ({placeholders})"
                                f" AND status = 'pending'"
                                f" RETURNING signal_id",
                                targets,
                            ).fetchall()
                            updated_ids = {row[0] for row in updated}
                            count = len(updated_ids)
                            st.success(f"{count} 件を cancelled に変更しました。")
                            skipped = len(targets) - count
                            if skipped > 0:
                                st.warning(
                                    f"{skipped} 件は既に pending ではなかったためスキップされました。"
                                )
                            del st.session_state["sq_cancel_targets"]
                            del st.session_state["sq_cancel_mode"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"キャンセル処理に失敗しました: {e}")
                with abort_col:
                    if st.button("戻る"):
                        del st.session_state["sq_cancel_targets"]
                        del st.session_state["sq_cancel_mode"]
                        st.rerun()

        # --- cancelled 物理削除 ---
        st.divider()
        st.subheader("Cancelled レコードの削除")

        cancelled_df = df[df["status"] == "cancelled"] if not df.empty else df
        cancelled_count = len(cancelled_df)

        if cancelled_count == 0:
            st.info("削除可能な cancelled レコードはありません。")
        else:
            st.caption(f"cancelled レコード: {cancelled_count} 件")
            if st.button(
                f"cancelled {cancelled_count} 件を完全削除",
                type="secondary",
            ):
                st.session_state["sq_delete_cancelled"] = True

            if st.session_state.get("sq_delete_cancelled"):
                st.warning(
                    f"cancelled レコード {cancelled_count} 件を完全削除します。"
                    "この操作は元に戻せません。"
                )
                del_col, abort_col = st.columns(2)
                with del_col:
                    if st.button("確定して削除実行", type="primary"):
                        try:
                            deleted = conn.execute(
                                "DELETE FROM signal_queue WHERE status = 'cancelled'"
                                " RETURNING signal_id"
                            ).fetchall()
                            st.success(f"{len(deleted)} 件を削除しました。")
                            st.session_state.pop("sq_delete_cancelled", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"削除処理に失敗しました: {e}")
                with abort_col:
                    if st.button("戻る", key="abort_delete"):
                        st.session_state.pop("sq_delete_cancelled", None)
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
