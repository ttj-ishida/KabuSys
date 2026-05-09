# AI Co-Pilot ウィザード（Phase 1-3）設計仕様

## Goal

`10_Strategy_Lab.py` に「AI Co-Pilot」タブを追加し、最新バックテスト結果をコンテキストとして OpenAI API に注入しながら、戦略パラメータのチューニング提案をチャット形式で行えるようにする。パラメータの自動反映・バックテスト再実行（Phase 4）は別 Issue とする。

## スコープ

### 含む（Phase 1-3）
- `backtest_summarizer.py`: DuckDB `backtest_runs` から最新1件の要約 Markdown 生成
- `components/ai_wizard.py`: 再利用可能な Streamlit チャットコンポーネント
- `10_Strategy_Lab.py`: 「AI Co-Pilot」タブ追加
- `monitoring.db`: `ai_wizard_messages` テーブルによる履歴永続化
- `schema.py`: DDL 追加
- OpenAI ストリーミング表示（`st.write_stream`）

### 含まない（Phase 4 / 別 Issue）
- AI 提案パラメータの `strategy_config.yaml` 自動反映
- バックテスト再実行ループ
- 変更前バックアップ・変更可能キー制限

## アーキテクチャ

```
10_Strategy_Lab.py
    └─ components/ai_wizard.render(duckdb_conn, sqlite_conn)
            ├─ backtest_summarizer.load_latest_summary(duckdb_conn) → Markdown
            ├─ monitoring_db: ai_wizard_messages 読み書き
            └─ OpenAI API (gpt-4o) ストリーミング
```

## ファイル構成

| 操作 | ファイル |
|------|---------|
| 新規 | `src/kabusys/ai/backtest_summarizer.py` |
| 新規 | `src/kabusys/monitoring/components/__init__.py` |
| 新規 | `src/kabusys/monitoring/components/ai_wizard.py` |
| 変更 | `src/kabusys/monitoring/monitoring_db.py`（`init_monitoring_db` に DDL 追加、`schema.py` 変更なし） |
| 変更 | `src/kabusys/monitoring/pages/10_Strategy_Lab.py` |
| 新規 | `tests/test_backtest_summarizer.py` |
| 新規 | `tests/test_ai_wizard.py` |
| 変更 | `tests/test_monitoring_db.py` |

## データ層

### `ai_wizard_messages` テーブル（monitoring.db / SQLite）

```sql
CREATE TABLE IF NOT EXISTS ai_wizard_messages (
    id          INTEGER   PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT      NOT NULL,
    role        TEXT      NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT      NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- `session_id`: `st.session_state` に UUID を持たせ、同一ブラウザセッションを束ねる
- ページリロード時は同じ `session_id` で履歴を復元する
- 「🗑 履歴クリア」ボタンで当該 `session_id` の行を全削除する

### `backtest_summarizer.py`

```python
def load_latest_summary(conn: duckdb.DuckDBPyConnection) -> str | None:
    """backtest_runs の最新1件から system prompt 用 Markdown を生成する。

    バックテスト結果がない場合は None を返す。
    params_json が不正な場合はパラメータ行をスキップし、クラッシュしない。
    """
```

注入するコンテキスト例：

```markdown
## 最新バックテスト結果（run_id: abc123, 2026-01-01〜2026-04-30）

| 指標 | 値 |
|------|-----|
| CAGR | +12.3% |
| Sharpe Ratio | 1.45 |
| Max Drawdown | -8.2% |
| Win Rate | 58.3% |
| Payoff Ratio | 1.82 |
| Profit Factor | 2.10 |
| Total Trades | 142 |

### 戦略パラメータ
**購入ロジック**: weights={momentum: 0.40, value: 0.30, quality: 0.20, ai: 0.10},
threshold=0.60, sector_boost=0.03, sector_quartile=0.25

**リスク・フィルター**: stop_loss_rate=-0.08, trailing_stop_atr_mult=2.0,
gap_up_threshold=0.04, gap_down_threshold=-0.04,
min_holding_days=5, max_holding_days=60,
topix_drawdown_threshold=-0.15, topix_size_multiplier_bear=0.5
```

## コンポーネント層

### `components/ai_wizard.py`

```python
def render(
    duckdb_conn: duckdb.DuckDBPyConnection,
    sqlite_conn: sqlite3.Connection,
) -> None:
    """AI Co-Pilot チャット UI を Streamlit に描画する。"""
```

**処理フロー：**

1. `session_id` を `st.session_state` に UUID で初期化（初回のみ）
2. SQLite から当該 `session_id` の履歴を読み込み `st.chat_message` で表示
3. `OPENAI_API_KEY` 未設定 → `st.error("OPENAI_API_KEY が設定されていません。環境変数を設定してください。")` で処理終了
4. `load_latest_summary(duckdb_conn)` で system prompt 生成
   - 結果なし → バックテスト未実行の旨を system prompt に記載（チャットは動作する）
5. `st.chat_input("KabuSysの戦略について質問してください")` でユーザー入力受付
6. ユーザーメッセージ → SQLite 保存 → OpenAI API 呼び出し
7. `st.write_stream` でレスポンスをストリーミング表示
8. アシスタントメッセージ → SQLite 保存

**system prompt テンプレート：**

```
あなたは KabuSys の戦略チューニング・アシスタントです。
以下のバックテスト結果を踏まえ、購入ロジック（weights / threshold / sector パラメータ）および
リスク・フィルターロジック（stop_loss / trailing_stop / gap / holding_days / topix パラメータ）の
改善案を提案してください。回答は簡潔な日本語で行い、具体的な数値変更案を含めてください。

{backtest_summary_markdown}
```

**サイドバー：**
- 「🗑 履歴クリア」ボタン → 当該 `session_id` の SQLite レコードを削除し `st.rerun()`

### `10_Strategy_Lab.py` の変更

既存の `tab_regime, tab_ai, tab_signals = st.tabs(...)` に `tab_copilot` を追加：

```python
# ファイル先頭のインポート追加
import sqlite3
from kabusys.monitoring.components.ai_wizard import render as render_wizard

# タブ定義（既存3タブに追加）
tab_regime, tab_ai, tab_signals, tab_copilot = st.tabs(
    ["市場レジーム", "AI スコア", "シグナル推移", "🤖 AI Co-Pilot"]
)

with tab_copilot:
    sqlite_conn = sqlite3.connect(str(settings.sqlite_path))
    try:
        render_wizard(conn, sqlite_conn)
    finally:
        sqlite_conn.close()
```

## テスト方針

### `tests/test_backtest_summarizer.py`

- `backtest_runs` にデータあり → Markdown に CAGR / Sharpe / Max Drawdown が含まれる
- `backtest_runs` にデータあり → 購入ロジック・フィルターロジック両方のパラメータが含まれる
- `backtest_runs` が空 → `None` を返す
- `params_json` が不正な JSON → クラッシュせず、パラメータ行なしで返す

### `tests/test_ai_wizard.py`

- `OPENAI_API_KEY` 未設定時 → `st.error` が呼ばれ、チャット入力が表示されない
- `session_id` が `st.session_state` に UUID として初期化される
- SQLite 履歴の保存・読み込みラウンドトリップ
- OpenAI API 呼び出しは `unittest.mock.patch` でモック（`news_nlp._call_openai_api` と同パターン）
- 履歴クリア → SQLite の当該 `session_id` レコードが削除される

### `tests/test_monitoring_db.py` への追加

- `ai_wizard_messages` テーブルの作成・INSERT・SELECT・DELETE スモークテスト

## バリデーション

| 条件 | 挙動 |
|------|------|
| `OPENAI_API_KEY` 未設定 | `st.error` 表示、チャット入力非表示 |
| `backtest_runs` が空 | system prompt に「バックテスト未実行」旨を記載、チャットは動作 |
| `params_json` が不正 JSON | パラメータ行をスキップ、Markdown の他部分は正常出力 |
| OpenAI API エラー | `st.error` でエラー内容を表示、履歴への保存はスキップ |

## Out of Scope

- パラメータ自動反映・バックテスト再実行（Phase 4 / 別 Issue）
- 設定ファイル変更前バックアップ（Phase 4 / 別 Issue）
- 変更可能キーの制限・破壊的変更防止（Phase 4 / 別 Issue）
- 複数バックテスト実行の比較・選択 UI
- LINE / メール通知との連携
