"""pages/3_Pre_Market.py — 朝の READY/BLOCKED 判定ページ。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.operations_data import load_premarket_data
from kabusys.operations.pre_market_report import (
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

st.set_page_config(page_title="Pre-Market", layout="wide", page_icon="🌅")
st.title("🌅 Pre-Market — 朝の確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    duckdb_conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    uri = Path(str(settings.sqlite_path)).resolve().as_uri() + "?mode=ro"
    sqlite_conn = sqlite3.connect(uri, uri=True)
except Exception as e:
    st.error(f"SQLite 接続失敗: {e}")
    duckdb_conn.close()
    st.stop()

try:
    result = load_premarket_data(duckdb_conn, sqlite_conn, settings)
except Exception as e:
    st.error(f"データ取得失敗: {e}")
    st.exception(e)
    duckdb_conn.close()
    sqlite_conn.close()
    st.stop()

status = result["status"]
if status == STATUS_READY:
    st.success("✅ READY — 執行開始可能")
elif status == STATUS_READY_WITH_WARNINGS:
    st.warning("⚠️ READY_WITH_WARNINGS — 警告を確認してください")
elif status == STATUS_BLOCKED:
    st.error("🚫 BLOCKED — 自動執行を開始しないでください")
else:
    st.error(f"🚫 {status} — 自動執行を開始しないでください")

st.divider()

checks = {c["name"]: c for c in result["checks"]}


def _icon(chk_status: str) -> str:
    return "✅" if chk_status == "ok" else ("⚠️" if chk_status == "warning" else "❌")


col1, col2, col3 = st.columns(3)
with col1:
    c = checks.get("data_freshness", {})
    st.metric(
        "データ鮮度",
        f"{_icon(c.get('status', 'failed'))} {'OK' if c.get('status') == 'ok' else '古い'}",
    )
with col2:
    c = checks.get("signal_queue", {})
    st.metric(
        "Signal Queue",
        f"{_icon(c.get('status', 'failed'))} pending {result['signal_queue_pending']}件",
    )
with col3:
    c = checks.get("task_scheduler", {})
    st.metric(
        "Task Scheduler",
        f"{_icon(c.get('status', 'failed'))} {'Ready' if c.get('status') == 'ok' else 'NG'}",
    )

col4, col5, col6 = st.columns(3)
with col4:
    c = checks.get("stop_flag", {})
    st.metric(
        "停止フラグ",
        f"{_icon(c.get('status', 'ok'))} {'あり' if result['stop_flag_exists'] else 'なし'}",
    )
with col5:
    st.metric("保有ポジション", f"📊 {result['position_count']}銘柄")
with col6:
    st.caption(f"生成: {result['generated_at']}")

if result["warnings"]:
    st.divider()
    st.subheader("⚠️ Warnings")
    for w in result["warnings"]:
        st.warning(w)

duckdb_conn.close()
sqlite_conn.close()
