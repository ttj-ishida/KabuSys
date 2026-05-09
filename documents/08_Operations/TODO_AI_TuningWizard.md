# AI Co-Pilot ウィザード（Risk & Strategy Co-Pilot）実装状況

## ステータス

- **Phase 1-3**: ✅ 実装済み（Issue #233 / PR #280、2026-05-09 main マージ）
- **Phase 4**: 未着手（Issue #279）

---

## 1. 背景と目的

KabuSysのキラーコンテンツとして、バックテスト結果を踏まえながら **AI（LLM）と対話して戦略パラメータをチューニングできるアシスタント機能** を構築する。外部の ChatGPT に頼らず、KabuSys 運用ダッシュボード（Streamlit）内の専用チャット UI として組み込む。

---

## 2. 実装済み機能（Phase 1-3）

### アーキテクチャ

```
10_Strategy_Lab.py
    └─ components/ai_wizard.render(duckdb_conn, sqlite_conn)
            ├─ ai/backtest_summarizer.load_latest_summary(duckdb_conn) → Markdown
            ├─ monitoring.db: ai_wizard_messages テーブル（履歴永続化）
            └─ OpenAI API (gpt-4o) ストリーミング
```

### 実装ファイル

| ファイル | 内容 |
|---------|------|
| `src/kabusys/ai/backtest_summarizer.py` | DuckDB `backtest_runs` 最新1件 → system prompt 用 Markdown 生成 |
| `src/kabusys/monitoring/components/ai_wizard.py` | Streamlit チャット UI コンポーネント（ストリーミング・履歴・API key バリデーション） |
| `src/kabusys/monitoring/monitoring_db.py` | `ai_wizard_messages` テーブル DDL + CRUD メソッド追加 |
| `src/kabusys/monitoring/pages/10_Strategy_Lab.py` | 「🤖 AI Co-Pilot」タブを第4タブとして追加 |

### 主な仕様

- **フロントエンド**: `st.chat_input` / `st.chat_message` / `st.write_stream`（ストリーミング）
- **LLM**: OpenAI GPT-4o（`OPENAI_API_KEY` 環境変数または `st.secrets` から取得）
- **コンテキスト注入**: 最新バックテスト結果（CAGR・Sharpe・Max Drawdown・Win Rate 等 + 戦略パラメータ）を system prompt に自動注入
- **履歴永続化**: SQLite `ai_wizard_messages` テーブル（セッション別・ページリロード後も復元）
- **履歴クリア**: タブ内「🗑 履歴クリア」ボタン
- **エラーハンドリング**: API key 未設定時は `st.error` + 早期 return、OpenAI エラーは UI に簡潔なメッセージ・詳細は `logging.exception`

---

## 3. 未実装機能（Phase 4 / Issue #279）

- AI 提案パラメータの `strategy_config.yaml` 自動反映
- 設定変更前の自動バックアップ機能
- AI が変更できるキーの制限・破壊的変更防止の仕組み
- バックテスト再実行ループ

---

## 4. 期待されるユースケース

- **ユーザー**: 「最近ドローダウンが大きいんだけど、どうすればいい？」
- **AI**: 「直近のバックテスト結果を見ると、ATRストップロスヒット率が急増しています。ATR乗数を1.5から2.0に広げてノイズを吸収することを提案します。」
- **ユーザー**: 「じゃあATRを2.0にした場合の効果を推測して」
