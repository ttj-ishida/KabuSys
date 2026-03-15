# KabuSys

日本株向け自動売買システム用ライブラリ（モジュール群）

このリポジトリはデータ取得・スキーマ管理・監査ログ・発注基盤など、自動売買システム構築に必要な共通機能をまとめた Python パッケージの一部です。J-Quants / kabuステーション 等の外部 API と連携し、DuckDB にデータを永続化するユーティリティを提供します。

主な設計方針の要点
- API レート制限・リトライ・トークン自動更新に対応（J-Quants クライアント）
- DuckDB を使った 3 層データモデル（Raw / Processed / Feature）と実行層・監査層のスキーマ定義
- データ取得と保存は冪等（ON CONFLICT DO UPDATE）を意識
- 監査ログは UUID 連鎖でシグナル → 発注 → 約定のトレーサビリティを保証
- すべてのタイムスタンプは UTC で扱う（監査系）

---

## 機能一覧

- 環境変数 / .env 管理
  - プロジェクトルートを探索して `.env` / `.env.local` を自動読み込み（必要に応じて無効化可）
- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）制御、リトライ（指数バックオフ）、401 時のリフレッシュ処理
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル作成 DDL を提供
  - 初期化（init_schema）や既存 DB への接続（get_connection）
  - インデックス定義付きでパフォーマンスを考慮
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化
  - 発注の冪等性（order_request_id）やステータス遷移を考慮
- ユーティリティ関数
  - 数値変換ヘルパー（_to_float/_to_int）など

---

## 必要条件

- Python 3.10 以上（型ヒントに union 演算子（|）などを利用）
- 主要依存ライブラリ（例）
  - duckdb
- 標準ライブラリ: urllib, json, datetime, logging など

インストール方法は後述のセットアップ参照。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに pyproject.toml / requirements.txt があればそれを利用してください。最小限は duckdb が必要です：
   ```
   pip install duckdb
   ```
   - 開発中でローカル編集を反映したい場合：
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - 必須環境変数（アプリケーションで参照されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack ボットトークン
     - SLACK_CHANNEL_ID      : 通知先 Slack チャネル ID
   - 任意 / 既定値あり:
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
     - DUCKDB_PATH (DuckDB ファイルパス) 既定: data/kabusys.duckdb
     - SQLITE_PATH (監視用 SQLite 等) 既定: data/monitoring.db
   - 自動 .env ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env`（上書き不可）→ `.env.local`（上書き可）の順に自動読み込みします。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（サンプル）

以下は主要ユースケースの抜粋例です。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は環境変数 DUCKDB_PATH を参照（既定: data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)
  ```

- J-Quants から日足を取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # 取得（銘柄・期間は任意）
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

  # DuckDB に保存（conn は init_schema の返り値）
  n_saved = save_daily_quotes(conn, records)
  print(f"saved {n_saved} rows")
  ```

- J-Quants の ID トークンを明示的に取得する
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 監査ログ（監査専用 DB）初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

重要ポイント
- J-Quants クライアントはレート制限を内部で待機（120 req/min）して順守します。
- HTTP エラー（408/429/5xx）に対して指数バックオフでリトライします。401 はトークンリフレッシュ後に 1 回だけ再試行します。
- DuckDB への挿入は ON CONFLICT DO UPDATE を使って冪等に保存します。
- 監査テーブルは UTC を前提にしています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

以下は主なファイル・モジュール（抜粋）です。実際のリポジトリでは他にもドキュメントやテストがあるかもしれません。

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数 / .env 読み込み・Settings
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント（取得＋保存ロジック）
      - schema.py                       # DuckDB スキーマ定義 & init_schema / get_connection
      - audit.py                        # 監査ログ（signal_events, order_requests, executions）
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

DuckDB テーブル要約（代表）
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査ログ: signal_events, order_requests, executions

---

## 補足 / ベストプラクティス

- 本ライブラリはデータプラットフォーム・自動売買の一部機能を提供するための基盤です。実際の取引ロジック（戦略実装・リスク管理・ブローカー接続）は別途実装してください。
- 環境変数の管理は慎重に行い、シークレット（トークン・パスワード）は公開リポジトリに含めないでください。
- DuckDB ファイルのバックアップやバージョン管理（マイグレーション）を計画してください。
- 監査データは削除しない運用（FK は ON DELETE RESTRICT）を前提としています。容量管理やアーカイブ方針を検討してください。

---

必要であれば、README に追加したい内容（例: CI / テスト実行方法、デプロイ手順、詳細な DDL 説明、サンプル .env.example）を教えてください。