"""monitoring/db_connect.py — DuckDB read-only 接続ヘルパー。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import streamlit as st

_LOCK_HINTS: tuple[str, ...] = (
    "already open",
    "is locked",
    "used by another process",
    "sharing violation",
    "winerror 32",
    "resource busy",
)


def connect_duckdb_ro(path: Path) -> duckdb.DuckDBPyConnection:
    """DuckDB を read-only で開く。

    ロック競合時は黄色警告を表示して st.stop()。
    ファイル不存在・権限エラーなど他の障害は赤エラーを表示して st.stop()。
    正常時は接続オブジェクトを返す。
    """
    if not path.exists():
        st.error("DuckDB ファイルが見つかりません。管理者に連絡してください。")
        st.stop()
    try:
        return duckdb.connect(str(path), read_only=True)
    except duckdb.Error as e:
        msg = str(e).lower()
        if any(h in msg for h in _LOCK_HINTS):
            st.warning(
                "⚙️ バッチまたは執行エンジンが DB を使用中のため、データを一時的に表示できません。"
                "しばらく待ってから **🔄 Refresh** してください。"
            )
        else:
            st.error("DuckDB 接続に失敗しました。管理者に連絡してください。")
        st.stop()
    except Exception:
        st.error("DuckDB 接続に失敗しました。管理者に連絡してください。")
        st.stop()
