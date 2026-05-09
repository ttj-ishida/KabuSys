"""ai_wizard.py — AI Co-Pilot チャットコンポーネント（再利用可能）。"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from typing import Generator

import duckdb
import streamlit as st
from openai import OpenAI

from kabusys.ai.backtest_summarizer import load_latest_summary
from kabusys.monitoring.monitoring_db import MonitoringDB

_logger = logging.getLogger(__name__)
_MODEL = "gpt-4o"

_SYSTEM_PROMPT_TEMPLATE = """\
あなたは KabuSys の戦略チューニング・アシスタントです。
以下のバックテスト結果を踏まえ、購入ロジック（weights / threshold / sector パラメータ）および
リスク・フィルターロジック（stop_loss / trailing_stop / gap / holding_days / topix パラメータ）の
改善案を提案してください。回答は簡潔な日本語で行い、具体的な数値変更案を含めてください。

{context}"""

_NO_DATA_CONTEXT = (
    "バックテスト結果がまだありません。一般的な戦略チューニングについて質問できます。"
)


def _stream_openai_response(
    client: OpenAI,
    messages: list[dict],
) -> Generator[str, None, None]:
    """OpenAI Chat Completions API をストリーミングで呼び出す。

    テスト時は
    unittest.mock.patch("kabusys.monitoring.components.ai_wizard._stream_openai_response")
    で差し替える。

    Yields:
        各チャンクのテキスト断片（content が None のチャンクはスキップ）。
    """
    stream = client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


def render(
    duckdb_conn: duckdb.DuckDBPyConnection,
    sqlite_conn: sqlite3.Connection,
) -> None:
    """AI Co-Pilot チャット UI を Streamlit に描画する。

    Args:
        duckdb_conn: DuckDB 接続（read_only=True 推奨）。backtest_runs を参照する。
        sqlite_conn: SQLite 接続（monitoring.db）。ai_wizard_messages を読み書きする。
    """
    if "wizard_session_id" not in st.session_state:
        st.session_state["wizard_session_id"] = str(uuid.uuid4())
    session_id: str = st.session_state["wizard_session_id"]

    db = MonitoringDB(sqlite_conn)

    with st.sidebar:
        if st.button("🗑 履歴クリア", key="wizard_clear"):
            db.clear_wizard_messages(session_id)
            st.session_state["wizard_session_id"] = str(uuid.uuid4())
            st.rerun()

    # st.rerun() が呼ばれなかった場合 (= ボタンを押さなかった場合) でも
    # session_state が更新されている可能性があるため、再取得する。
    session_id = st.session_state["wizard_session_id"]

    api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error("OPENAI_API_KEY が設定されていません。環境変数を設定してください。")
        return

    summary = load_latest_summary(duckdb_conn)
    context = summary if summary is not None else _NO_DATA_CONTEXT
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(context=context)

    history = db.load_wizard_messages(session_id)
    for msg in history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("KabuSysの戦略について質問してください")
    if not user_input:
        return

    with st.chat_message("user"):
        st.write(user_input)
    db.save_wizard_message(session_id, "user", user_input)

    client = OpenAI(api_key=api_key)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_input})

    try:
        with st.chat_message("assistant"):
            response_text = st.write_stream(_stream_openai_response(client, messages))
        if response_text:
            db.save_wizard_message(session_id, "assistant", str(response_text))
    except Exception:
        _logger.exception("OpenAI API 呼び出しに失敗しました")
        st.error(
            "OpenAI API の呼び出しに失敗しました。しばらく経ってから再度お試しください。"
        )
