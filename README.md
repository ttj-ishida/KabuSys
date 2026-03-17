# KabuSys

KabuSys は日本株のデータ収集・品質管理・自動売買パイプラインを提供するライブラリです。J-Quants API や RSS フィードを使ったデータ取得、DuckDB を用いたスキーマ定義・永続化、ETL（差分更新）と品質チェック、そして監査ログ（発注→約定のトレーサビリティ）に重点を置いた設計になっています。

主な設計方針:
- API レート制限・リトライ・トークン自動リフレッシュを組み込み
- データ取得は冪等（ON CONFLICT）で保存
- ニュース収集は SSRF / XML 攻撃対策・サイズ制限を実装
- すべての時刻は UTC を基本としたトレーサビリティ確保

バージョン: 0.1.0

---

## 機能一覧

- J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限（120 req/min）・指数バックオフ・401 時のトークン自動リフレッシュ
  - ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT）
- DuckDB スキーマ管理 / 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックスも定義
- ETL パイプライン
  - 差分取得（最終取得日 + バックフィル）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去・記事IDは SHA-256 の一部
  - defusedxml による XML 脆弱性対策
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁の日本株コード）
- マーケットカレンダー管理（営業日判定／前後営業日取得）
- 監査ログ（signal → order_request → executions）スキーマと初期化
- 設定管理モジュール
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須項目は settings オブジェクト経由で取得可能

---

## 必要条件 / 依存

- Python 3.9+（型注釈にパイプ型等を使用しているため）
- duckdb
- defusedxml
- 標準ライブラリ（urllib, json, logging, datetime など）

（実運用では追加の依存やテスト用の依存がある可能性があります。setup を用意している場合はそちらの requirements を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注周りで使用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

   .env の例（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema を実行してテーブルを作成します（親ディレクトリがなければ自動作成されます）。

   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査ログを分離 DB に作る場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡単なコード例）

- J-Quants の ID トークンを取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- DuckDB スキーマの初期化（上記参照）

- 日次ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は以下を行います:
    1. market_calendar を先読みして更新
    2. 株価日足の差分取得（backfill を含む）
    3. 財務データの差分取得
    4. 品質チェック（デフォルトで実行）
  - ETL の個別呼び出しも可能:
    - run_calendar_etl, run_prices_etl, run_financials_etl

- ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  known_codes = {"7203", "6758", ...}  # 必要なら有効コードセットを渡す
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存数, ...}
  ```

- ニュース単体フェッチ:
  ```python
  from kabusys.data.news_collector import fetch_rss, save_raw_news
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  saved_ids = save_raw_news(conn, articles)
  ```

- 監査ログ（発注／約定）テーブルの初期化:
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  ```

---

## 設計上の注意 / 運用メモ

- API レートリミット:
  - J-Quants クライアントは 120 req/min を固定間隔スロットリングで守ります。
- リトライ・エラー処理:
  - ネットワーク系 (408/429/5xx) は最大 3 回の指数バックオフリトライ。
  - 401 は自動的にリフレッシュして1回だけリトライ。
- データの冪等性:
  - raw テーブルへの保存は ON CONFLICT DO UPDATE / DO NOTHING を用いており再実行が安全な設計です。
- News Collector の安全対策:
  - XML パーサに defusedxml を使用
  - 応答サイズ上限（10MB）を超える場合はスキップ
  - リダイレクトや最終ホストがプライベートアドレスの場合は拒否（SSRF 対策）
- 時刻の扱い:
  - 取得時刻（fetched_at / created_at）は UTC ベースで記録する方針です（監査ログは明示的に UTC にセットします）。
- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。環境変数で上書き保護されます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - audit.py                 — 監査ログ（signal/order_request/executions）スキーマ
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py              — 発注/実行層（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視関連（拡張ポイント）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの検出は __file__ から親を辿って行われます。ワークディレクトリに依存しない方式です。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。
- DuckDB テーブルが作成されない
  - schema.init_schema() を必ず実行してください。get_connection() は初期化を行いません。
- J-Quants の 401 が発生する
  - get_id_token() は settings.jquants_refresh_token を使います。トークンが不正または期限切れの場合は設定を確認してください。jquants_client は 401 を受けると自動でリフレッシュを試みます（1回分）。

---

## 貢献 / 拡張ポイント

- strategy/ 下に独自の戦略モジュールを追加し、signals を生成して signal_queue に投入することで発注フローと連携できます。
- execution/ 下でブローカー API ラッパーを実装し、order_requests を外部に送信／executions を取り込むロジックを実装してください。
- monitoring/ で Prometheus Exporter やアラートロジックを実装できます。

---

ご質問や追加のドキュメント（例: API 使用例、CI/デプロイ手順、テストガイドなど）が必要であればお知らせください。README の補足部分（例: requirements.txt、セットアップスクリプト、.env.example）も作成できます。