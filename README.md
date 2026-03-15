# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得、DBスキーマ管理、監査ログ、戦略／実行／モニタリングの基盤を提供します。

主な設計方針：
- J-Quants API からのデータ取得（OHLCV、財務データ、マーケットカレンダー）
- DuckDB を用いたローカル永続化（冪等性を意識した INSERT/UPDATE）
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なクライアント
- 監査ログ（signal → order_request → execution）のトレーサビリティ確保

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須 env の取得とバリデーション（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL の検証とヘルパープロパティ（is_live など）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - rate limiting（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対応）
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）
  - ページネーション対応の取得関数
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB へ保存する冪等的な save_* 関数
    - save_daily_quotes
    - save_financial_statements
    - save_market_calendar
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) でテーブルとインデックスを冪等に作成
  - get_connection(db_path) で既存 DB へ接続
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の初期化
  - init_audit_schema(conn) / init_audit_db(db_path)
  - 監査用インデックス群の定義
- パッケージ骨組み（strategy, execution, monitoring） — 拡張ポイント

---

## セットアップ手順

前提
- Python 3.10 以上（| 型注釈などを利用）
- duckdb パッケージ

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb
# 開発時にパッケージを編集しながら使う場合:
# pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : environment（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を上位で検出）を基準に `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数（最優先） > .env.local（上書き） > .env（既存変数のみセット）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

.env のパース仕様（互換性）
- export KEY=val 形式に対応
- シングル/ダブルクォートをサポート（バックスラッシュエスケープ対応）
- 行末コメントをサポート（クォート無しの値で '#' の直前が空白/タブの場合はコメントと扱う）

例: .env.example（README に貼るサンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 以降、conn を使って保存処理などを呼び出せます
```

2) J-Quants から日足を取得して保存する（簡易例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 例: 単一銘柄を指定（code に None を渡すと全銘柄取得）
records = fetch_daily_quotes(code="7203")  # トヨタ（例）
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データ・カレンダーの取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

records_f = fetch_financial_statements(date_from=..., date_to=..., code="7203")
save_financial_statements(conn, records_f)

records_cal = fetch_market_calendar()
save_market_calendar(conn, records_cal)
```

4) 監査ログの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

注意点
- fetch_* 系は内部で rate limiter と retry を行います。高頻度実行時は設計通りの制限内で動かしてください。
- get_id_token() は内部で settings.jquants_refresh_token を参照します。安全な取り扱いを行ってください（秘密情報はリポジトリに置かない）。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live, is_paper, is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str|None, code: str|None, date_from: date|None, date_to: date|None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> duckdb connection

---

## ディレクトリ構成

プロジェクト内の主要ファイル／ディレクトリ（本リポジトリのスニペットに基づく）
```
src/
  kabusys/
    __init__.py               # パッケージ定義（version 等）
    config.py                 # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
      schema.py               # DuckDB スキーマ定義・初期化
      audit.py                # 監査ログ（signal/order_request/execution）
      monitoring/             # 監視機能用（未実装のプレースホルダ）
    strategy/                  # 戦略ロジック（プレースホルダ）
    execution/                 # 発注実行ロジック（プレースホルダ）
    monitoring/                # モニタリング（プレースホルダ）
```

テーブル分類（概略）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 注意事項 / ベストプラクティス

- 機密情報（API トークン等）は .env に置いても安全に管理してください。公開リポジトリにアップロードしないでください。
- DuckDB ファイルを共有する場合はファイルロックや整合性に注意してください（複数プロセスで同時書き込みする設計は検討が必要です）。
- 本ライブラリは API の呼び出しで rate limit や retry を組み込んでいますが、J-Quants の利用規約やレート制限は常に確認してください。
- 監査ログは削除しない前提です。保持方針やディスク容量に注意してください。

---

必要があれば、README にサンプルスクリプトや CI 設定、より詳細なデータフロー図（DataSchema.md、DataPlatform.md 参照）を追加できます。どの情報を追加したいか教えてください。