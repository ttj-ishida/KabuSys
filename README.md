# KabuSys

日本株自動売買システム向けの軽量ライブラリコアです。  
データ取得・永続化、スキーマ定義、監査ログ（トレーサビリティ）、環境設定など、取引システムの基盤機能を提供します。

主な用途:
- J-Quants API からのマーケットデータ取得（OHLCV、財務、マーケットカレンダー）
- DuckDB を用いたデータレイクスキーマの初期化・永続化
- 発注フローを含む監査ログ（order_request → executions のトレース）
- 環境変数ベースの設定管理（.env を自動ロード）

---

## 機能一覧

- 環境/設定管理
  - .env, .env.local をプロジェクトルートから自動読み込み（起点は .git または pyproject.toml）
  - 読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - `.env` パースの特徴: `export KEY=val`、クォート内のエスケープ、行内コメント処理 等

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）・401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止

- DuckDB スキーマ (`kabusys.data.schema`)
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義
  - 冪等なテーブル作成（CREATE TABLE IF NOT EXISTS）
  - インデックスを含む初期化 API: `init_schema(db_path)`、`:memory:` 対応

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - signal_events / order_requests / executions の監査テーブル
  - order_request_id を冪等キーとして二重発注を防止
  - UTC タイムスタンプ、FK の ON DELETE RESTRICT 方針
  - 既存接続に対する `init_audit_schema(conn)`、専用 DB の `init_audit_db(path)` を提供

- DB 保存ユーティリティ
  - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（いずれも冪等的に INSERT ... ON CONFLICT DO UPDATE）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 環境（推奨: 仮想環境）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール  
   本プロジェクトでは少なくとも `duckdb` が必要です。その他の HTTP 周りは標準ライブラリを利用しています。
   ```
   pip install duckdb
   ```
   ※ 実運用では logging や Slack 連携などを追加インストールする場合があります。

4. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml のある階層）に `.env` または `.env.local` を作成してください。必須の環境変数は以下の通りです。

   必須:
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API パスワード
   - SLACK_BOT_TOKEN        — Slack ボットトークン
   - SLACK_CHANNEL_ID       — Slack チャネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV            — 実行環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL      — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

   自動ロードを無効化する（テスト時など）場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（例）

Python スクリプト内での基本的な利用例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は Path を返す（デフォルト: data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)
  ```

- J-Quants から日足取得して DuckDB に保存
  ```python
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved_count = save_daily_quotes(conn, records)
  print(f"saved {saved_count} rows")
  ```

- ID トークン取得（明示的に）
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 監査ログの初期化（既存 DuckDB 接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema() で得た接続
  init_audit_schema(conn)
  ```

実際の取引・発注ロジックは strategy / execution モジュールで実装される想定です（本コードベースでは該当パッケージは空の __init__ が用意されています）。

---

## 設定（settings）について

`kabusys.config.settings` から設定にアクセスできます。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuAPI 用パスワード（必須）
- kabu_api_base_url: kabuAPI のベース URL（デフォルト提供）
- slack_bot_token / slack_channel_id: Slack 通知用（必須）
- duckdb_path / sqlite_path: DB ファイルパス（Path オブジェクト）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（検証済み値のみ許可）
- is_live / is_paper / is_dev: 環境判定ヘルパ

注意: settings は必須環境変数が未設定の場合に ValueError を投げます。

---

## スキーマ（主なテーブル一覧）

重要なテーブル（抜粋）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions

- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols

- Feature Layer
  - features, ai_scores

- Execution Layer
  - signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance

- 監査ログ
  - signal_events, order_requests, executions

全テーブルは `kabusys.data.schema.init_schema()` で作成され、`ON CONFLICT` を用いた冪等的な保存方法をサポートします。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（src 側）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各モジュールの役割:
- config.py: 環境変数/設定の読み込みロジック
- data/jquants_client.py: J-Quants API クライアントおよび DuckDB 保存関数
- data/schema.py: DuckDB スキーマ定義・初期化
- data/audit.py: 監査ログテーブル定義・初期化
- strategy / execution / monitoring: 上位層の実装場所（拡張用）

---

## 注意事項 / 実運用上のポイント

- J-Quants のレート制限（120 req/min）を尊重する実装になっています。大量取得時はスロットリングの影響があります。
- API 呼び出しは最大 3 回のリトライを行い、401 時はトークンを自動リフレッシュして再試行します。
- DuckDB パスの親ディレクトリは自動作成されます。`:memory:` を渡すとインメモリ DB になります。
- 監査ログは削除しない前提です（FK は ON DELETE RESTRICT）。監査データの管理・バックアップ方針を設計段階で定めてください。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます（CI や特殊配置に注意）。

---

この README は本コードベースの機能紹介と基本的な使い方をまとめたものです。戦略や発注ロジックを実装する際は、監査ログと DB スキーマに則って冪等性とトレーサビリティを確保することを推奨します。