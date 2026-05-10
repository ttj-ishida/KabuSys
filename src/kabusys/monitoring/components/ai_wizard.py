"""ai_wizard.py — AI Co-Pilot チャットコンポーネント（再利用可能）。"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Generator

import duckdb
import streamlit as st
from openai import OpenAI

from kabusys.ai.backtest_summarizer import load_latest_summary
from kabusys.ai.param_extractor import extract_params
from kabusys.monitoring.components.param_review import render_param_review
from kabusys.monitoring.monitoring_db import MonitoringDB

_logger = logging.getLogger(__name__)
_MODEL = "gpt-4o"

_SYSTEM_PROMPT_TEMPLATE = """\
あなたは KabuSys の戦略チューニング・アシスタントです。
以下のバックテスト結果を踏まえ、購入ロジック（weights / threshold / sector パラメータ）および
リスク・フィルターロジック（stop_loss / trailing_stop / gap / holding_days / topix パラメータ）の
改善案を提案してください。回答は簡潔な日本語で行い、具体的な数値変更案を含めてください。

{context}

改善案がある場合は、回答末尾に必ず以下の形式で JSON ブロックを出力してください。
変更不要なパラメータは含めないでください。
weights は変更する重みキーのみ含めてください（例: {{"weights": {{"momentum": 0.45}}}}）。

```json
{{"threshold": 0.65, "trailing_stop_atr_mult": 2.5}}
```"""

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


def _load_prev_run_id(conn: duckdb.DuckDBPyConnection) -> str | None:
    """backtest_runs の最新 run_id を取得する。"""
    try:
        row = conn.execute(
            "SELECT run_id FROM backtest_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return str(row[0]) if row else None
    except Exception:
        return None


def render(
    duckdb_conn: duckdb.DuckDBPyConnection,
    sqlite_conn: sqlite3.Connection,
    duckdb_path: Path,
    config_path: Path,
) -> None:
    """AI Co-Pilot チャット UI を Streamlit に描画する。

    Args:
        duckdb_conn:  DuckDB 接続（read_only=True 推奨）。backtest_runs を参照する。
        sqlite_conn:  SQLite 接続（monitoring.db）。ai_wizard_messages を読み書きする。
        duckdb_path:  subprocess に渡す DuckDB ファイルパス。
        config_path:  strategy_config.yaml の Path。config_manager に渡す。
    """
    if "wizard_session_id" not in st.session_state:
        st.session_state["wizard_session_id"] = str(uuid.uuid4())
    session_id: str = st.session_state["wizard_session_id"]

    db = MonitoringDB(sqlite_conn)

    api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error(
            "OPENAI_API_KEY が設定されていません。"
            "環境変数または st.secrets に設定してください。"
        )
        return

    if st.button("🗑 履歴クリア", key="wizard_clear"):
        db.clear_wizard_messages(session_id)
        st.session_state["wizard_session_id"] = str(uuid.uuid4())
        st.rerun()

    session_id = st.session_state["wizard_session_id"]

    prev_run_id = _load_prev_run_id(duckdb_conn)
    summary = load_latest_summary(duckdb_conn)
    context = summary if summary is not None else _NO_DATA_CONTEXT
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(context=context)

    history = db.load_wizard_messages(session_id)
    for msg in history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 保留中の提案または適用済み状態があれば param_review を常時表示
    if st.session_state.get("param_review_suggested") or st.session_state.get(
        "param_review_applied"
    ):
        render_param_review(
            suggested_params=st.session_state.get("param_review_suggested", {}),
            config_path=config_path,
            duckdb_path=duckdb_path,
            prev_run_id=prev_run_id,
        )

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
            suggested = extract_params(str(response_text))
            if suggested:
                st.session_state["param_review_suggested"] = suggested
                st.rerun()
    except Exception:
        _logger.exception(
            "OpenAI API 呼び出しに失敗しました (session_id=%s)", session_id
        )
        st.error(
            "OpenAI API の呼び出しに失敗しました。しばらく経ってから再度お試しください。"
        )
