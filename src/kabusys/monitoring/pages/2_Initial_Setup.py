"""pages/2_Initial_Setup.py — 環境設定・DB・Task Scheduler 確認ページ。"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from kabusys.config import Settings
from kabusys.operations.pre_market_collector import check_task_scheduler
from kabusys.validate_config import run_checks

st.set_page_config(page_title="Initial Setup", layout="wide", page_icon="⚙️")
st.title("⚙️ Initial Setup — 環境確認")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    result = run_checks()
except Exception as e:
    st.error(f"設定検証の実行に失敗しました: {e}")
    st.stop()

if result.status == "OK":
    st.success("✅ OK — すべての設定が正常です")
elif result.status == "WARNING":
    st.warning(f"⚠️ WARNING — 警告 {len(result.warnings)} 件")
else:
    st.error(f"🚫 ERROR — エラー {len(result.errors)} 件")

tab_env, tab_yaml, tab_db, tab_scheduler = st.tabs(
    ["環境変数", "設定ファイル", "DB ファイル", "Task Scheduler"]
)

_REQUIRED = {"JQUANTS_REFRESH_TOKEN", "KABU_API_PASSWORD"}
_OPTIONAL = {
    "KABUSYS_ENV",
    "DUCKDB_PATH",
    "SQLITE_PATH",
    "LOG_LEVEL",
    "KABU_API_BASE_URL",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_USER_ID",
    "ENABLE_YAHOONEWS",
    "KABU_USE_SANDBOX",
    "KABU_SANDBOX_API_PASSWORD",
    "PAPER_TRADING_INITIAL_CASH",
}

with tab_env:
    st.subheader("必須環境変数")
    for var in sorted(_REQUIRED):
        if os.environ.get(var, ""):
            st.success(f"✅ {var}: 設定済み")
        else:
            st.error(f"❌ {var}: 未設定")
    st.subheader("オプション環境変数")
    for var in sorted(_OPTIONAL):
        if os.environ.get(var, ""):
            st.info(f"✅ {var}: 設定済み")
        else:
            st.caption(f"　{var}: 未設定（デフォルト値を使用）")

_CONFIG_FILES = [
    "system_config.yaml",
    "data_config.yaml",
    "strategy_config.yaml",
    "risk_config.yaml",
    "execution_config.yaml",
    "monitoring_config.yaml",
]

with tab_yaml:
    st.subheader("設定ファイル (config/*.yaml)")
    for f in _CONFIG_FILES:
        if (Path("config") / f).exists():
            st.success(f"✅ {f}")
        else:
            st.warning(
                f"⚠️ {f}: 見つかりません（python scripts/generate_config.py で生成）"
            )
    if result.errors or result.warnings:
        st.divider()
        for msg in result.errors:
            st.error(msg)
        for msg in result.warnings:
            st.warning(msg)

with tab_db:
    st.subheader("DB ファイル")
    _db_checks = [
        (Path(str(settings.duckdb_path)), "DuckDB (kabusys.duckdb)", True),
        (Path(str(settings.sqlite_path)), "SQLite monitoring (monitoring.db)", False),
        (
            Path(str(settings.paper_sqlite_path)),
            "SQLite paper (paper_trading.db)",
            False,
        ),
    ]
    for p, label, required in _db_checks:
        if p.exists():
            size_kb = p.stat().st_size // 1024
            st.success(f"✅ {label}: {size_kb} KB")
        elif required:
            st.error(f"❌ {label}: 見つかりません")
        else:
            st.warning(
                f"⚠️ {label}: 見つかりません（paper_trading 環境以外は不要な場合あり）"
            )

with tab_scheduler:
    st.subheader("Task Scheduler")
    try:
        ready = check_task_scheduler("KabuSys_ExecutionStart")
        if ready:
            st.success("✅ KabuSys_ExecutionStart: Ready")
        else:
            st.error("❌ KabuSys_ExecutionStart: Ready ではありません（要確認）")
    except Exception as e:
        st.warning(
            f"Task Scheduler の確認に失敗しました（Windows 環境外では利用不可）: {e}"
        )
