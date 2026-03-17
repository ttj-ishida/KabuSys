# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、DuckDB スキーマ・監査ログなど、自動売買システムのバックエンド基盤を提供します。

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの市場データ・財務データ・マーケットカレンダーの取得（レートリミット・リトライ・トークン自動更新対応）
- RSS からのニュース収集と記事の前処理・銘柄紐付け（SSRF対策・XML脆弱性対策・サイズ制限）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）スキーマの定義・初期化
- ETL パイプライン（差分更新、バックフィル、保存、品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日検索・夜間バッチ更新）
- 監査ログ（信号 → 発注 → 約定のトレーサビリティ）用スキーマ

ライブラリは冪等性（ON CONFLICT / DO UPDATE 等）や Look-ahead Bias 回避の観点（fetched_at の記録）を重視して設計されています。

## 主な機能一覧

- データ取得
  - J-Quants から株価（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得（ページネーション対応）
  - レート制限（120 req/min）と自動リトライ（指数バックオフ）、401 の場合はトークン自動リフレッシュ
- データ格納
  - DuckDB に対するスキーマ定義と初期化（raw_prices / raw_financials / market_calendar / features / signals / orders / trades / positions など）
  - 冪等な保存メソッド（ON CONFLICT で更新）
- ETL パイプライン
  - 差分更新・バックフィル（デフォルト 3 日）・品質チェック実行（欠損・スパイク・重複・日付不整合）
  - run_daily_etl により日次 ETL を一括実行
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事ID の正規化（URL 正規化 → SHA-256 の先頭 32 文字）、DuckDB への保存
  - SSRF 防御、XML の安全なパース（defusedxml）、レスポンスサイズ制限
  - 銘柄コード抽出（4 桁数字）と news_symbols への紐付け
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間更新
- 監査ログ
  - signal_events, order_requests, executions など監査用テーブル。UTC タイムゾーン固定。

## セットアップ手順

前提：Python 3.9+（型注釈の union 演算子などの使用に合わせること）を推奨します。

1. リポジトリをチェックアウト
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール  
   最低限必要なパッケージは duckdb と defusedxml 等です。プロジェクトに requirements.txt がある場合はそちらを使ってください。

   pip install duckdb defusedxml

   （プロジェクトを editable インストールする場合）
   pip install -e .

4. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化可能）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack Bot Token（通知用）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

   任意（デフォルト有り）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

   自動読み込みを無効にする:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env の読み込みは優先順位:
   OS 環境変数 > .env.local > .env

   例 (.env):
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=./data/kabusys.duckdb

## 使い方（基本例）

以下は代表的な使い方サンプルです。実行は Python REPL やスクリプト内で行います。

- DuckDB スキーマ初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # :memory: を指定するとインメモリ DB を利用できます

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  オプション例:
  result = run_daily_etl(conn, target_date=date(2026, 1, 1), run_quality_checks=True)

- J-Quants の ID トークン取得
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得します

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄抽出のための有効な銘柄コード集合を渡す
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(stats)  # {source_name: 新規保存件数}

- 監査ログスキーマ初期化（監査専用DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

ログレベルは環境変数 LOG_LEVEL で制御されます。

## よく使う API（抜粋）

- kabusys.config.settings: 環境変数アクセス用の Settings インスタンス
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.data.news_collector.save_raw_news(conn, articles)
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- kabusys.data.calendar_management.calendar_update_job(conn)
- kabusys.data.audit.init_audit_db(db_path), init_audit_schema(conn)

各関数の docstring を参照してください（引数・戻り値・副作用の詳細が記載されています）。

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py              -- 環境変数・設定管理（.env 自動読み込みなど）
    - data/
      - __init__.py
      - jquants_client.py    -- J-Quants API クライアント、取得/保存ロジック
      - news_collector.py    -- RSS 収集、前処理、DuckDB 保存
      - schema.py            -- DuckDB スキーマ定義・初期化
      - pipeline.py          -- ETL パイプライン（差分更新、品質チェック）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
      - audit.py             -- 監査ログ（signal/order/execution）スキーマ初期化
      - quality.py           -- データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py          -- 戦略関連（拡張ポイント）
    - execution/
      - __init__.py          -- 発注/ブローカ連携（拡張ポイント）
    - monitoring/
      - __init__.py          -- 監視用コード置き場（拡張ポイント）

## 運用上の注意点

- 環境変数の管理: .env/.env.local に機密情報を記載する場合は適切なアクセス管理を行ってください。OS 環境変数が常に優先されます。
- レート制限: J-Quants の制限（120 req/min）を遵守するために RateLimiter を実装しています。多重並列処理での過度な同時呼び出しに注意してください。
- DuckDB のトランザクション: 一部の初期化関数は transactional オプションを持ち、外部からのトランザクション制御に依存します。呼び出し時はドキュメントの注意書きを参照してください。
- セキュリティ: RSS 取得時は SSRF 対策や defusedxml を利用しており、レスポンスサイズの上限を設けていますが、未知のフィードへの接続には十分注意してください。
- 時刻: 監査ログや fetched_at は UTC を想定して扱っています。

## 開発・拡張ポイント

- strategy/ と execution/ は骨組みとして用意されています。ここに売買戦略やブローカー連携ロジックを実装してください。
- monitoring モジュールは監視・アラート用の拡張ポイントです（Slack 通知など）。

---

その他、各モジュールの詳細な設計原則やエラーハンドリング方針はソースコード内の docstring に記載されています。実運用前に J-Quants と kabuステーションの認証フロー、API 利用条件、監査要件（保存保持期間等）を確認してください。