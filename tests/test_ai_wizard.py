"""ai_wizard コンポーネント単体テスト（Issue #233）"""

from __future__ import annotations

import os
import sqlite3
import uuid
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def wizard_sqlite():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def wizard_duckdb():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE backtest_runs (
            run_id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            start_date DATE NOT NULL, end_date DATE NOT NULL,
            initial_cash DECIMAL(18,2) NOT NULL, scope_mode VARCHAR NOT NULL,
            scope_codes_json VARCHAR, params_json VARCHAR NOT NULL,
            cagr DOUBLE, sharpe DOUBLE, max_drawdown DOUBLE,
            win_rate DOUBLE, payoff_ratio DOUBLE, profit_factor DOUBLE,
            annual_volatility DOUBLE, calmar_ratio DOUBLE,
            avg_holding_days DOUBLE, total_trades INTEGER,
            effective_universe_size INTEGER
        )
    """)
    yield conn
    conn.close()


def _make_st_mock(session_state=None):
    """st モジュールのモックを生成する。"""
    mock_st = MagicMock()
    mock_st.session_state = session_state if session_state is not None else {}
    mock_st.sidebar.__enter__ = MagicMock(return_value=None)
    mock_st.sidebar.__exit__ = MagicMock(return_value=False)
    mock_st.chat_message.return_value.__enter__ = MagicMock(return_value=None)
    mock_st.chat_message.return_value.__exit__ = MagicMock(return_value=False)
    mock_st.chat_input.return_value = None
    return mock_st


class TestRenderApiKeyMissing:
    def test_shows_error_when_no_api_key(self, wizard_duckdb, wizard_sqlite):
        import kabusys.monitoring.components.ai_wizard as mod

        mock_st = _make_st_mock()
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(mod, "st", mock_st):
                mod.render(wizard_duckdb, wizard_sqlite)

        mock_st.error.assert_called_once()
        assert "OPENAI_API_KEY" in mock_st.error.call_args[0][0]

    def test_returns_early_without_chat_input(self, wizard_duckdb, wizard_sqlite):
        """API キー未設定時はチャット入力が表示されない（return early）。"""
        import kabusys.monitoring.components.ai_wizard as mod

        mock_st = _make_st_mock()
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(mod, "st", mock_st):
                mod.render(wizard_duckdb, wizard_sqlite)

        mock_st.chat_input.assert_not_called()


class TestSessionIdInitialization:
    def test_session_id_set_as_uuid(self, wizard_duckdb, wizard_sqlite):
        """初回呼び出しで wizard_session_id が UUID として session_state に設定される。"""
        import kabusys.monitoring.components.ai_wizard as mod

        state: dict = {}
        mock_st = _make_st_mock(session_state=state)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(mod, "st", mock_st):
                mod.render(wizard_duckdb, wizard_sqlite)

        assert "wizard_session_id" in state
        uuid.UUID(state["wizard_session_id"])  # 不正なら ValueError


class TestStreamOpenaiResponse:
    def test_yields_content_strings_and_skips_none(self):
        """_stream_openai_response がコンテンツを yield し、None チャンクをスキップする。"""
        from kabusys.monitoring.components.ai_wizard import _stream_openai_response

        chunk1 = MagicMock()
        chunk1.choices[0].delta.content = "テスト"
        chunk2 = MagicMock()
        chunk2.choices[0].delta.content = None
        chunk3 = MagicMock()
        chunk3.choices[0].delta.content = "回答"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]

        result = list(
            _stream_openai_response(mock_client, [{"role": "user", "content": "test"}])
        )
        assert result == ["テスト", "回答"]

    def test_calls_openai_with_stream_true(self):
        """_stream_openai_response が stream=True で API を呼び出す。"""
        from kabusys.monitoring.components.ai_wizard import _stream_openai_response

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = []

        list(_stream_openai_response(mock_client, []))

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("stream") is True


class TestRenderWithApiKey:
    def test_saves_user_and_assistant_to_sqlite(self, wizard_duckdb, wizard_sqlite):
        """render でユーザー入力 → AI 応答が SQLite に保存される。"""
        import kabusys.monitoring.components.ai_wizard as mod

        state: dict = {}
        mock_st = _make_st_mock(session_state=state)
        mock_st.chat_input.return_value = "ドローダウンを改善したい"
        mock_st.write_stream.return_value = "ATR乗数を2.0から2.5にすることを提案します。"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(mod, "st", mock_st):
                with patch(
                    "kabusys.monitoring.components.ai_wizard._stream_openai_response",
                    return_value=iter(["ATR乗数を2.0から2.5にすることを提案します。"]),
                ):
                    with patch("kabusys.monitoring.components.ai_wizard.OpenAI"):
                        mod.render(wizard_duckdb, wizard_sqlite)

        session_id = state["wizard_session_id"]
        db = MonitoringDB(wizard_sqlite)
        msgs = db.load_wizard_messages(session_id)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "ドローダウンを改善したい"
        assert msgs[1]["role"] == "assistant"


class TestHistoryClear:
    def test_clear_button_deletes_session_messages(self, wizard_duckdb, wizard_sqlite):
        """履歴クリアボタン押下 → SQLite の当該 session_id レコードが削除される。"""
        import kabusys.monitoring.components.ai_wizard as mod

        session_id = str(uuid.uuid4())
        db = MonitoringDB(wizard_sqlite)
        db.save_wizard_message(session_id, "user", "テストメッセージ")
        assert len(db.load_wizard_messages(session_id)) == 1

        state: dict = {"wizard_session_id": session_id}
        mock_st = _make_st_mock(session_state=state)
        mock_st.button.return_value = True  # simulate clear button click
        mock_st.chat_input.return_value = None  # no user input

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(mod, "st", mock_st):
                with patch(
                    "kabusys.monitoring.components.ai_wizard.load_latest_summary",
                    return_value=None,
                ):
                    mod.render(wizard_duckdb, wizard_sqlite)

        assert db.load_wizard_messages(session_id) == []
