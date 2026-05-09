# AI Co-Pilot ウィザード（Phase 1-3）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strategy Lab ページに「🤖 AI Co-Pilot」タブを追加し、最新バックテスト結果を OpenAI の system prompt に自動注入しながら戦略チューニングをチャット形式で支援する。

**Architecture:** `backtest_summarizer.py` が DuckDB から最新バックテスト結果を Markdown 化して system prompt に注入し、`components/ai_wizard.py` が Streamlit チャット UI とストリーミング呼び出し・SQLite 履歴管理を担う。`10_Strategy_Lab.py` は 4 番目のタブでコンポーネントを呼び出すだけの薄い層。

**Tech Stack:** Python 3.10+, DuckDB, SQLite, Streamlit, openai Python SDK (`openai.OpenAI`)

---

## ファイル構成

| 操作 | ファイル | 責務 |
|------|---------|------|
| 変更 | `src/kabusys/monitoring/monitoring_db.py` | `ai_wizard_messages` テーブル + 履歴 CRUD メソッド追加 |
| 新規 | `src/kabusys/ai/backtest_summarizer.py` | DuckDB → system prompt 用 Markdown 生成 |
| 新規 | `src/kabusys/monitoring/components/__init__.py` | パッケージ宣言 |
| 新規 | `src/kabusys/monitoring/components/ai_wizard.py` | 再利用可能 Streamlit チャットコンポーネント |
| 変更 | `src/kabusys/monitoring/pages/10_Strategy_Lab.py` | 4 番目のタブ追加 |
| 変更 | `tests/test_monitoring_db.py` | wizard 履歴 CRUD テスト追記 |
| 新規 | `tests/test_backtest_summarizer.py` | 要約生成テスト |
| 新規 | `tests/test_ai_wizard.py` | コンポーネントテスト |

---

### Task 1: ai_wizard_messages テーブル + MonitoringDB 拡張

**Files:**
- Modify: `src/kabusys/monitoring/monitoring_db.py`
- Modify: `tests/test_monitoring_db.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_monitoring_db.py` のファイル末尾に以下を追記する。

```python
class TestWizardMessages:
    def test_save_and_load_messages(self, monitoring_conn):
        """save → load でメッセージが時系列順に返る。"""
        db = MonitoringDB(monitoring_conn)
        db.save_wizard_message("sess1", "user", "テスト質問")
        db.save_wizard_message("sess1", "assistant", "テスト回答")
        msgs = db.load_wizard_messages("sess1")
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "テスト質問"}
        assert msgs[1] == {"role": "assistant", "content": "テスト回答"}

    def test_load_empty_session(self, monitoring_conn):
        """存在しない session_id は空リストを返す。"""
        db = MonitoringDB(monitoring_conn)
        assert db.load_wizard_messages("nonexistent") == []

    def test_clear_removes_only_target_session(self, monitoring_conn):
        """clear は対象 session_id のみ削除し、別セッションは残る。"""
        db = MonitoringDB(monitoring_conn)
        db.save_wizard_message("sess1", "user", "question")
        db.save_wizard_message("sess2", "user", "other")
        db.clear_wizard_messages("sess1")
        assert db.load_wizard_messages("sess1") == []
        assert len(db.load_wizard_messages("sess2")) == 1

    def test_ai_wizard_messages_table_exists(self, monitoring_conn):
        """init_monitoring_db 後に ai_wizard_messages テーブルが存在する。"""
        tables = {
            row[0]
            for row in monitoring_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "ai_wizard_messages" in tables
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_monitoring_db.py::TestWizardMessages -v
```

期待: `AttributeError: 'MonitoringDB' object has no attribute 'save_wizard_message'`

- [ ] **Step 3: `init_monitoring_db` に `ai_wizard_messages` テーブルを追加**

`src/kabusys/monitoring/monitoring_db.py` の `init_monitoring_db` 関数内の
`conn.executescript("""` ブロックの末尾（`dashboard` テーブルの `);` の直後、
閉じる `"""` の直前）に以下を追加する：

```python
        CREATE TABLE IF NOT EXISTS ai_wizard_messages (
            id          INTEGER   PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT      NOT NULL,
            role        TEXT      NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content     TEXT      NOT NULL,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_wizard_messages_session
            ON ai_wizard_messages (session_id, created_at);
```

- [ ] **Step 4: `MonitoringDB` クラスに 3 メソッドを追加**

`src/kabusys/monitoring/monitoring_db.py` の `MonitoringDB` クラスの末尾（`get_dashboard` メソッドの後）に以下を追加する：

```python
    def save_wizard_message(self, session_id: str, role: str, content: str) -> None:
        """AI ウィザードの発言を ai_wizard_messages テーブルに保存する。"""
        self._conn.execute(
            "INSERT INTO ai_wizard_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self._conn.commit()

    def load_wizard_messages(self, session_id: str) -> list[dict]:
        """session_id に紐づく発言履歴を時系列順で返す。

        Returns:
            [{"role": "user"|"assistant", "content": "..."}, ...]
        """
        rows = self._conn.execute(
            "SELECT role, content FROM ai_wizard_messages "
            "WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def clear_wizard_messages(self, session_id: str) -> None:
        """session_id に紐づく全発言を削除する。"""
        self._conn.execute(
            "DELETE FROM ai_wizard_messages WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()
```

- [ ] **Step 5: テストが PASS することを確認**

```bash
pytest tests/test_monitoring_db.py::TestWizardMessages -v
```

期待: 4 テスト全 PASS

- [ ] **Step 6: 全テストで回帰がないことを確認**

```bash
pytest tests/test_monitoring_db.py -v
```

期待: 全 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/monitoring/monitoring_db.py tests/test_monitoring_db.py
git commit -m "feat: ai_wizard_messages テーブル + MonitoringDB 履歴 CRUD (Issue #233)"
```

---

### Task 2: backtest_summarizer.py

**Files:**
- Create: `src/kabusys/ai/backtest_summarizer.py`
- Create: `tests/test_backtest_summarizer.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest_summarizer.py` を新規作成する：

```python
"""backtest_summarizer 単体テスト（Issue #233）"""

from __future__ import annotations

import json

import duckdb
import pytest

from kabusys.ai.backtest_summarizer import load_latest_summary

_BACKTEST_RUNS_DDL = """
    CREATE TABLE backtest_runs (
        run_id                  VARCHAR       PRIMARY KEY,
        created_at              TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        start_date              DATE          NOT NULL,
        end_date                DATE          NOT NULL,
        initial_cash            DECIMAL(18,2) NOT NULL,
        scope_mode              VARCHAR       NOT NULL,
        scope_codes_json        VARCHAR,
        params_json             VARCHAR       NOT NULL,
        cagr                    DOUBLE,
        sharpe                  DOUBLE,
        max_drawdown            DOUBLE,
        win_rate                DOUBLE,
        payoff_ratio            DOUBLE,
        profit_factor           DOUBLE,
        annual_volatility       DOUBLE,
        calmar_ratio            DOUBLE,
        avg_holding_days        DOUBLE,
        total_trades            INTEGER,
        effective_universe_size INTEGER
    )
"""

_SAMPLE_PARAMS = {
    "weights": {"momentum": 0.4, "value": 0.3, "quality": 0.2, "ai": 0.1},
    "threshold": 0.60,
    "sector_boost": 0.03,
    "sector_quartile": 0.25,
    "stop_loss_rate": -0.08,
    "trailing_stop_atr_mult": 2.0,
    "gap_up_threshold": 0.04,
    "gap_down_threshold": -0.04,
    "min_holding_days": 5,
    "max_holding_days": 60,
    "topix_drawdown_threshold": -0.15,
    "topix_size_multiplier_bear": 0.5,
}


@pytest.fixture
def bt_conn():
    conn = duckdb.connect(":memory:")
    conn.execute(_BACKTEST_RUNS_DDL)
    yield conn
    conn.close()


def _insert_run(conn, run_id="r1", params=None):
    p = params if params is not None else _SAMPLE_PARAMS
    conn.execute(
        """
        INSERT INTO backtest_runs (
            run_id, start_date, end_date, initial_cash, scope_mode, params_json,
            cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor, total_trades
        ) VALUES (?, '2026-01-01', '2026-04-30', 1000000, 'default_universe', ?,
                  0.123, 1.45, -0.082, 0.583, 1.82, 2.10, 142)
        """,
        [run_id, json.dumps(p)],
    )


class TestLoadLatestSummary:
    def test_returns_none_when_empty(self, bt_conn):
        assert load_latest_summary(bt_conn) is None

    def test_contains_cagr(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "+12.30%" in result

    def test_contains_sharpe_and_drawdown(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert "1.450" in result
        assert "-8.20%" in result

    def test_contains_win_rate_and_trades(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert "58.30%" in result
        assert "142" in result

    def test_contains_buy_logic_params(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "threshold=0.6" in result
        assert "sector_boost=0.03" in result

    def test_contains_risk_filter_params(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "stop_loss_rate=-0.08" in result
        assert "trailing_stop_atr_mult=2.0" in result
        assert "topix_drawdown_threshold=-0.15" in result

    def test_invalid_params_json_no_crash(self, bt_conn):
        bt_conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash, scope_mode, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor, total_trades
            ) VALUES ('r_bad', '2026-01-01', '2026-04-30', 1000000, 'default_universe',
                      'INVALID_JSON', 0.10, 1.0, -0.05, 0.5, 1.5, 1.8, 100)
            """
        )
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "CAGR" in result

    def test_returns_latest_when_multiple_runs(self, bt_conn):
        _insert_run(bt_conn, run_id="r_old")
        newer_params = dict(_SAMPLE_PARAMS, threshold=0.70)
        bt_conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash, scope_mode, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor,
                total_trades, created_at
            ) VALUES ('r_new', '2026-01-01', '2026-04-30', 1000000, 'default_universe',
                      ?, 0.20, 1.8, -0.06, 0.60, 2.0, 2.5, 180,
                      current_timestamp + INTERVAL 1 SECOND)
            """,
            [json.dumps(newer_params)],
        )
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "r_new" in result
        assert "threshold=0.7" in result
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_backtest_summarizer.py -v
```

期待: `ModuleNotFoundError: No module named 'kabusys.ai.backtest_summarizer'`

- [ ] **Step 3: `backtest_summarizer.py` を実装する**

`src/kabusys/ai/backtest_summarizer.py` を新規作成する：

```python
"""backtest_summarizer.py — バックテスト結果から AI system prompt 用 Markdown を生成する。"""

from __future__ import annotations

import json
import logging

import duckdb

logger = logging.getLogger(__name__)


def load_latest_summary(conn: duckdb.DuckDBPyConnection) -> str | None:
    """backtest_runs の最新1件から system prompt 用 Markdown を生成する。

    バックテスト結果がない場合は None を返す。
    params_json が不正な場合はパラメータ行をスキップし、クラッシュしない。

    Args:
        conn: DuckDB 接続。backtest_runs テーブルを参照する。

    Returns:
        Markdown 形式の文字列、またはデータなしの場合は None。
    """
    try:
        row = conn.execute("""
            SELECT run_id, start_date, end_date,
                   cagr, sharpe, max_drawdown, win_rate,
                   payoff_ratio, profit_factor, total_trades,
                   params_json
            FROM backtest_runs
            ORDER BY created_at DESC
            LIMIT 1
        """).fetchone()
    except Exception as e:
        logger.warning("load_latest_summary: backtest_runs 読み込みエラー: %s", e)
        return None

    if row is None:
        return None

    run_id = str(row[0])
    start_date = str(row[1])
    end_date = str(row[2])
    cagr: float | None = row[3]
    sharpe: float | None = row[4]
    max_dd: float | None = row[5]
    win_rate: float | None = row[6]
    payoff: float | None = row[7]
    profit_factor: float | None = row[8]
    total_trades: int | None = row[9]
    params_json_str: str | None = row[10]

    def _pct(v: float | None) -> str:
        return f"{v:+.2%}" if v is not None else "N/A"

    def _f(v: float | None, prec: int = 3) -> str:
        return f"{v:.{prec}f}" if v is not None else "N/A"

    lines = [
        f"## 最新バックテスト結果（run_id: {run_id}, {start_date}〜{end_date}）",
        "",
        "| 指標 | 値 |",
        "|------|-----|",
        f"| CAGR | {_pct(cagr)} |",
        f"| Sharpe Ratio | {_f(sharpe)} |",
        f"| Max Drawdown | {_pct(max_dd)} |",
        f"| Win Rate | {_pct(win_rate)} |",
        f"| Payoff Ratio | {_f(payoff)} |",
        f"| Profit Factor | {_f(profit_factor)} |",
        f"| Total Trades | {total_trades if total_trades is not None else 'N/A'} |",
    ]

    params: dict = {}
    if params_json_str:
        try:
            parsed = json.loads(params_json_str)
            if isinstance(parsed, dict):
                params = parsed
        except (json.JSONDecodeError, TypeError):
            logger.warning("load_latest_summary: params_json のパースに失敗しました")

    if params:
        weights = params.get("weights", {})
        buy_parts = [
            f"weights={weights}",
            f"threshold={params.get('threshold', 'N/A')}",
            f"sector_boost={params.get('sector_boost', 'N/A')}",
            f"sector_quartile={params.get('sector_quartile', 'N/A')}",
        ]
        risk_parts = [
            f"stop_loss_rate={params.get('stop_loss_rate', 'N/A')}",
            f"trailing_stop_atr_mult={params.get('trailing_stop_atr_mult', 'N/A')}",
            f"gap_up_threshold={params.get('gap_up_threshold', 'N/A')}",
            f"gap_down_threshold={params.get('gap_down_threshold', 'N/A')}",
            f"min_holding_days={params.get('min_holding_days', 'N/A')}",
            f"max_holding_days={params.get('max_holding_days', 'N/A')}",
            f"topix_drawdown_threshold={params.get('topix_drawdown_threshold', 'N/A')}",
            f"topix_size_multiplier_bear={params.get('topix_size_multiplier_bear', 'N/A')}",
        ]
        lines += [
            "",
            "### 戦略パラメータ",
            f"**購入ロジック**: {', '.join(buy_parts)}",
            "",
            f"**リスク・フィルター**: {', '.join(risk_parts)}",
        ]

    return "\n".join(lines)
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
pytest tests/test_backtest_summarizer.py -v
```

期待: 8 テスト全 PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/ai/backtest_summarizer.py tests/test_backtest_summarizer.py
git commit -m "feat: backtest_summarizer — バックテスト結果→system prompt Markdown生成 (Issue #233)"
```

---

### Task 3: components/ai_wizard.py

**Files:**
- Create: `src/kabusys/monitoring/components/__init__.py`
- Create: `src/kabusys/monitoring/components/ai_wizard.py`
- Create: `tests/test_ai_wizard.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ai_wizard.py` を新規作成する：

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
pytest tests/test_ai_wizard.py -v
```

期待: `ModuleNotFoundError: No module named 'kabusys.monitoring.components'`

- [ ] **Step 3: `components/__init__.py` を作成する**

`src/kabusys/monitoring/components/__init__.py` を空ファイルとして作成する：

```python
```

（空ファイル）

- [ ] **Step 4: `ai_wizard.py` を実装する**

`src/kabusys/monitoring/components/ai_wizard.py` を新規作成する：

```python
"""ai_wizard.py — AI Co-Pilot チャットコンポーネント（再利用可能）。"""

from __future__ import annotations

import os
import sqlite3
import uuid
from typing import Generator

import duckdb
import streamlit as st
from openai import OpenAI

from kabusys.ai.backtest_summarizer import load_latest_summary
from kabusys.monitoring.monitoring_db import MonitoringDB

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
        st.session_state.wizard_session_id = str(uuid.uuid4())
    session_id: str = st.session_state.wizard_session_id

    db = MonitoringDB(sqlite_conn)

    with st.sidebar:
        if st.button("🗑 履歴クリア", key="wizard_clear"):
            db.clear_wizard_messages(session_id)
            st.session_state.wizard_session_id = str(uuid.uuid4())
            st.rerun()

    api_key = os.environ.get("OPENAI_API_KEY")
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
        db.save_wizard_message(session_id, "assistant", str(response_text))
    except Exception as e:
        st.error(f"OpenAI API エラー: {e}")
```

- [ ] **Step 5: テストが PASS することを確認**

```bash
pytest tests/test_ai_wizard.py -v
```

期待: 7 テスト全 PASS

- [ ] **Step 6: 全テストで回帰がないことを確認**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -20
```

期待: 全 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/monitoring/components/ tests/test_ai_wizard.py
git commit -m "feat: ai_wizard コンポーネント — Streamlit チャット UI + OpenAI ストリーミング (Issue #233)"
```

---

### Task 4: 10_Strategy_Lab.py — AI Co-Pilot タブ統合

**Files:**
- Modify: `src/kabusys/monitoring/pages/10_Strategy_Lab.py`

- [ ] **Step 1: ファイルを読んで現状を確認する**

`src/kabusys/monitoring/pages/10_Strategy_Lab.py` を開く。現在の先頭部分：

```python
"""pages/4_Strategy_Lab.py — 市場レジーム・AI スコア・戦略状態ビュー。"""

from __future__ import annotations

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.strategy_lab_data import (
    load_ai_scores,
    load_market_regime,
    load_signal_summary,
)
```

- [ ] **Step 2: インポートに `sqlite3` と `render_wizard` を追加する**

`src/kabusys/monitoring/pages/10_Strategy_Lab.py` のインポートブロックを以下に変更する（`import duckdb` の前に `import sqlite3` を追加し、`render_wizard` のインポートを末尾に追加）：

```python
"""pages/4_Strategy_Lab.py — 市場レジーム・AI スコア・戦略状態ビュー。"""

from __future__ import annotations

import sqlite3

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.components.ai_wizard import render as render_wizard
from kabusys.monitoring.strategy_lab_data import (
    load_ai_scores,
    load_market_regime,
    load_signal_summary,
)
```

- [ ] **Step 3: タブ定義に `tab_copilot` を追加する**

現在のタブ定義：

```python
    tab_regime, tab_ai, tab_signals = st.tabs(
        ["市場レジーム", "AI スコア", "シグナル推移"]
    )
```

これを以下に変更する：

```python
    tab_regime, tab_ai, tab_signals, tab_copilot = st.tabs(
        ["市場レジーム", "AI スコア", "シグナル推移", "🤖 AI Co-Pilot"]
    )
```

- [ ] **Step 4: `tab_copilot` の実装を追加する**

既存の `with tab_signals:` ブロックの直後（`finally:` の前）に以下を追加する：

```python
    with tab_copilot:
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
        try:
            render_wizard(conn, sqlite_conn)
        finally:
            sqlite_conn.close()
```

変更後のファイル全体：

```python
"""pages/4_Strategy_Lab.py — 市場レジーム・AI スコア・戦略状態ビュー。"""

from __future__ import annotations

import sqlite3

import duckdb
import streamlit as st

from kabusys.config import Settings
from kabusys.monitoring.components.ai_wizard import render as render_wizard
from kabusys.monitoring.strategy_lab_data import (
    load_ai_scores,
    load_market_regime,
    load_signal_summary,
)

st.set_page_config(page_title="Strategy Lab", layout="wide", page_icon="📊")
st.title("📊 Strategy Lab — 市場レジーム・AI スコア")

settings = Settings()
with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    days = st.selectbox("表示期間", [14, 30, 60], index=1)
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
except Exception as e:
    st.error(f"DuckDB 接続失敗: {e}")
    st.stop()

try:
    tab_regime, tab_ai, tab_signals, tab_copilot = st.tabs(
        ["市場レジーム", "AI スコア", "シグナル推移", "🤖 AI Co-Pilot"]
    )

    with tab_regime:
        df = load_market_regime(conn, days=days)
        if df.empty:
            st.info("レジームデータがありません。")
        else:
            latest = df.iloc[-1]
            col1, col2 = st.columns(2)
            col1.metric("最新レジームスコア", f"{float(latest['regime_score']):.3f}")
            col2.metric("レジームラベル", latest["regime_label"])
            st.subheader("レジームスコア推移")
            st.line_chart(df.set_index("date")["regime_score"])
            st.dataframe(df, use_container_width=True)

    with tab_ai:
        df = load_ai_scores(conn)
        if df.empty:
            st.info(
                "AI スコアデータがありません（ENABLE_AI_SENTIMENT=false の場合は空）。"
            )
        else:
            st.caption(f"基準日: {df['date'].iloc[0]}")
            col1, col2 = st.columns(2)
            col1.metric("スコア最高銘柄", df.iloc[0]["code"])
            col2.metric("最高 AI スコア", f"{float(df.iloc[0]['ai_score']):.3f}")
            st.dataframe(df, use_container_width=True)

    with tab_signals:
        df = load_signal_summary(conn, days=days)
        if df.empty:
            st.info("シグナルデータがありません。")
        else:
            total_buy = int(df["buy_count"].sum())
            total_sell = int(df["sell_count"].sum())
            col1, col2 = st.columns(2)
            col1.metric(f"買いシグナル合計（{days}日）", total_buy)
            col2.metric(f"売りシグナル合計（{days}日）", total_sell)
            st.subheader("日別シグナル件数")
            st.bar_chart(df.set_index("date")[["buy_count", "sell_count"]])

    with tab_copilot:
        sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
        try:
            render_wizard(conn, sqlite_conn)
        finally:
            sqlite_conn.close()

finally:
    conn.close()
```

- [ ] **Step 5: ruff チェック**

```bash
python -m ruff check src/kabusys/monitoring/pages/10_Strategy_Lab.py
python -m ruff format --check src/kabusys/monitoring/pages/10_Strategy_Lab.py
```

期待: `All checks passed!`

- [ ] **Step 6: 全テストが PASS することを確認**

```bash
pytest tests/ --tb=short 2>&1 | tail -10
```

期待: 全 PASS

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/monitoring/pages/10_Strategy_Lab.py
git commit -m "feat: Strategy Lab に AI Co-Pilot タブを追加 (Issue #233)"
```
