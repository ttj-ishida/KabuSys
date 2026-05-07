"""pages/4_Execution_Startup.py — 起動直後の差分確認ページ。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_execution_startup
from kabusys.operations.execution_startup_report import (
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

st.set_page_config(page_title="Execution Startup", layout="wide", page_icon="🚀")
st.title("🚀 Execution Startup — 起動確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    selected_date = st.date_input("対象日", value=date.today())
    if st.button("🔄 Refresh"):
        st.rerun()

base_dir = Path("artifacts/execution_startup")
report_data = load_execution_startup(base_dir, target_date=selected_date)

if report_data is None:
    st.info(f"📋 {selected_date} の Execution はまだ起動していません。")
    st.caption("Execution を起動すると `artifacts/execution_startup/{date}/summary.json` が自動生成されます。")
    st.stop()

status = report_data.get("status", "BLOCKED")
if status == STATUS_READY:
    st.success("✅ READY — 執行開始可能")
elif status == STATUS_READY_WITH_WARNINGS:
    st.warning("⚠️ READY_WITH_WARNINGS — ポジション差分あり。確認してください")
else:
    st.error("🚫 BLOCKED — ステータス不明注文あり。手動確認が必要です")

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("注文同期数", report_data.get("orders_synced", 0))
col2.metric("ステータス不明注文", report_data.get("orders_no_status", 0))
col3.metric("ポジション差分件数", len(report_data.get("position_discrepancies", [])))

discrepancies = report_data.get("position_discrepancies", [])
if discrepancies:
    st.subheader("ポジション差分")
    st.dataframe(discrepancies, use_container_width=True)

warnings = report_data.get("warnings", [])
if warnings:
    st.divider()
    st.subheader("⚠️ Warnings")
    for w in warnings:
        st.warning(w)

st.caption(f"生成: {report_data.get('generated_at', 'N/A')}")
