"""pages/12_Manual_Trades.py — 手動約定入力・確認ビュー。

表示は常に read-only 接続（connect_duckdb_ro）で行い、read-write 接続（init_schema）は
登録・削除・ステータス変更ボタンのハンドラ内でのみ開く。執行エンジンや夜間バッチが
DB をロック中の場合は警告を出してページはクラッシュさせない。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import TypeVar

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.data.schema import init_schema
from kabusys.monitoring.dashboard_data import (
    load_manual_actions,
    load_manual_positions,
)
from kabusys.monitoring.db_connect import connect_duckdb_ro
from kabusys.operations.manual_trades import (
    DuplicateManualTradeError,
    ManualTradeInput,
    add_manual_trade,
    delete_manual_trade,
    list_manual_trades,
    update_manual_action_status,
)

st.set_page_config(page_title="Manual Trades", layout="wide", page_icon="📝")
st.title("📝 Manual Trades — 手動約定")

settings = Settings()

_T = TypeVar("_T")
_DB_BUSY_MESSAGE = (
    "⚙️ バッチまたは執行エンジンが DB を使用中のため、書き込めませんでした。"
    "しばらく待ってから再度実行してください。"
)


def _run_write(action: Callable[[duckdb.DuckDBPyConnection], _T]) -> tuple[bool, _T | None]:
    """read-write 接続を開いて action を実行する。

    ロック競合・I/O エラー時は st.warning を表示して (False, None) を返す。
    業務例外（DuplicateManualTradeError / ValueError など）は呼び出し側へ伝播する。
    """
    try:
        conn = init_schema(settings.duckdb_path)
    except (duckdb.IOException, OSError) as exc:
        st.warning(f"{_DB_BUSY_MESSAGE}（{exc}）")
        return False, None
    try:
        return True, action(conn)
    except (duckdb.IOException, OSError) as exc:
        st.warning(f"{_DB_BUSY_MESSAGE}（{exc}）")
        return False, None
    finally:
        conn.close()


with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

tab_add, tab_positions, tab_actions, tab_history = st.tabs(
    ["入力", "手動ポジション", "売却候補", "履歴"]
)

with tab_add:
    st.subheader("手動約定を入力")

    with st.form("manual_trade_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_date = st.date_input("約定日", value=date.today())
            code = st.text_input("銘柄コード", placeholder="7203")
        with col2:
            side = st.selectbox("売買", ["buy", "sell"])
            qty = st.number_input("数量", min_value=1, step=100, value=100)
        with col3:
            price = st.number_input("約定単価", min_value=0.0, step=1.0, value=0.0)
            fees = st.number_input("手数料", min_value=0.0, step=1.0, value=0.0)

        source_signal_id = st.text_input("Signal ID（任意）")
        note = st.text_input("メモ（任意）")
        force = st.checkbox("同一IDがある場合は上書きする")
        submitted = st.form_submit_button("登録")

    if submitted:
        if not code.strip():
            st.error("銘柄コードを入力してください。")
        else:
            payload = ManualTradeInput(
                trade_date=trade_date,
                code=code,
                side=side,
                qty=int(qty),
                price=float(price),
                fees=float(fees),
                source_signal_id=source_signal_id.strip() or None,
                note=note.strip() or None,
            )
            try:
                ok, trade_id = _run_write(lambda c: add_manual_trade(c, payload, force=force))
            except (DuplicateManualTradeError, ValueError) as exc:
                st.error(str(exc))
            else:
                if ok:
                    st.success(f"登録しました: {trade_id}")

with tab_positions:
    st.subheader("手動ポジション")
    valuation_date = st.date_input(
        "評価日",
        value=date.today() - timedelta(days=1),
        help="この日以前で最新の終値を使って評価します。",
    )
    conn = connect_duckdb_ro(settings.duckdb_path)
    try:
        df = load_manual_positions(conn, as_of=valuation_date)
    finally:
        conn.close()

    if df.empty:
        st.info("手動ポジションはありません。")
    else:
        total_pnl = df["total_pnl"].sum(min_count=1)
        unrealized_pnl = df["unrealized_pnl"].sum(min_count=1)
        realized_pnl = df["realized_pnl"].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "含み損益",
            f"{unrealized_pnl:,.0f}円" if unrealized_pnl == unrealized_pnl else "-",
        )
        col2.metric("実現損益", f"{realized_pnl:,.0f}円")
        col3.metric("合計損益", f"{total_pnl:,.0f}円" if total_pnl == total_pnl else "-")
        st.dataframe(df, use_container_width=True)

_REASON_LABELS = {
    "stop_loss": "損切り",
    "trailing_stop": "トレーリング",
    "time_exit": "保有期限",
    "score_drop": "スコア低下",
    "earnings_avoidance": "決算回避",
}

with tab_actions:
    st.subheader("手動売却候補")
    st.caption(
        "KabuSys は発注しません。証券画面で手動売却後、約定を「入力」タブで登録してください。"
    )
    show_all = st.checkbox("対応済み・見送りも表示", value=False, key="actions_show_all")
    filter_by_date = st.checkbox("日付で絞り込む", value=False, key="actions_filter_by_date")
    action_date = (
        st.date_input("対象日", value=date.today(), key="actions_target_date")
        if filter_by_date
        else None
    )
    conn = connect_duckdb_ro(settings.duckdb_path)
    try:
        # 日付で絞り込まない場合、毎晩候補に残る銘柄が重複しないよう銘柄ごとに最新行のみ表示
        actions = load_manual_actions(
            conn,
            target_date=action_date,
            status=None if show_all else "open",
            latest_per_code=not filter_by_date,
        )
    finally:
        conn.close()

    if actions.empty:
        st.info("売却候補はありません。")
    else:
        for row in actions.itertuples():
            reason = _REASON_LABELS.get(row.reason, row.reason)
            cols = st.columns([4, 1, 1])
            cols[0].write(f"{row.date} **{row.code}** {row.qty}株 — {reason}（{row.status}）")
            for col, label, new_status in (
                (cols[1], "対応済み", "done"),
                (cols[2], "見送り", "skipped"),
            ):
                if col.button(
                    label, key=f"{new_status}_{row.action_id}", disabled=row.status == new_status
                ):
                    ok, _ = _run_write(
                        lambda c, aid=row.action_id, s=new_status: update_manual_action_status(
                            c, aid, s
                        )
                    )
                    if ok:
                        st.rerun()

with tab_history:
    st.subheader("手動約定履歴")
    conn = connect_duckdb_ro(settings.duckdb_path)
    try:
        rows = list_manual_trades(conn)
    finally:
        conn.close()

    if not rows:
        st.info("手動約定履歴はありません。")
    else:
        for row in rows[:100]:
            with st.expander(f"{row.trade_date} {row.code} {row.side} {row.qty}株"):
                st.write(
                    {
                        "trade_id": row.trade_id,
                        "price": row.price,
                        "fees": row.fees,
                        "source_signal_id": row.source_signal_id,
                        "note": row.note,
                        "created_at": row.created_at,
                    }
                )
                if st.button("削除", key=f"delete_{row.trade_id}"):
                    ok, _ = _run_write(lambda c, tid=row.trade_id: delete_manual_trade(c, tid))
                    if ok:
                        st.success(f"削除しました: {row.trade_id}")
                        st.rerun()
