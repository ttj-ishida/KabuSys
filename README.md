# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル算出、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査ログなど、研究→運用までのパイプラインを想定したモジュールを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「テスト容易性」「外部 API への慎重な依存（リトライ・レート制御）」です。

## 主な機能一覧
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、ページネーション）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次 ETL：株価、財務、カレンダー）
- 特徴量エンジニアリング（factor 正規化・ユニバースフィルタ）
- シグナル生成（ファクター・AI スコア統合、BUY/SELL 判定、冪等な signals 保存）
- ニュース収集（RSS 取得、前処理、SSRF 対策、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day）
- 各種統計ユーティリティ（Z スコア正規化、IC / rank / summary）
- 監査ログ・トレーサビリティ（signal → order → execution の追跡用テーブル群）

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール  
   最低限必要なパッケージ（プロジェクトの pyproject.toml がある想定です）:
   ```
   pip install duckdb defusedxml
   ```
   開発環境では他にもロギング周りやテストツールを追加してください。

3. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主に必要な環境変数は以下です（必須は明示）。

   必須（Settings.require を参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=DEBUG
   ```

4. データベース初期化（DuckDB）
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   ":memory:" を渡すとインメモリ DB を使えます（テスト用途）。

## 使い方（典型的なワークフロー）

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- 特徴量の構築（feature layer へのアップサート）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  # conn は init_schema で得た DuckDB 接続
  n = build_features(conn, date(2024, 1, 31))
  print(f"upserted features: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, date(2024, 1, 31))
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)  # {source: saved_count}
  ```

- カレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からの直接取得と保存（低レベル）
  ```python
  from kabusys.data import jquants_client as jq

  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

注意: ほとんどの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。トランザクション管理は関数内で行われることが多いですが、必要に応じて明示的に開始/コミット/ロールバックすることもできます。

## ディレクトリ構成（主要ファイルと概要）

src/kabusys/
- __init__.py
  - パッケージ初期化（version 等）
- config.py
  - 環境変数読み込み・Settings クラス（必須設定の検証、自動 .env ロード）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
  - news_collector.py
    - RSS フィード取得、記事前処理、raw_news 保存、銘柄抽出
  - schema.py
    - DuckDB の DDL 定義と init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management.py
    - market_calendar の管理・営業日判定・calendar_update_job
  - audit.py
    - 監査ログ関連の DDL（signal_events / order_requests / executions 等）
  - features.py
    - データ層向けの特徴量ユーティリティ公開（再エクスポート）
- research/
  - __init__.py
  - factor_research.py
    - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials 参照）
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py
    - ファクターの統合・正規化・ユニバースフィルタ・features への upsert
  - signal_generator.py
    - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成・保存
- execution/
  - （発注／ブローカー連携用モジュールを配置想定）
- monitoring/
  - （監視・メトリクス保存用モジュールを配置想定）

各モジュールの詳細はソース内の docstring に設計目的・処理フロー・注意点が記載されています。実運用前にこれらドキュメントを一読してください。

## 開発・テストに関する補足
- 多くの関数は外部 API（J-Quants や RSS）に依存するため、ユニットテストでは API 呼び出しをモックしてテストする設計になっています（例: jquants_client のトークンキャッシュや news_collector._urlopen の差し替え）。
- .env 自動読み込み機能はテストのために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB の ":memory:" はテスト向けに便利です。

---

この README はコードベース内の docstring と設計ノートを要約したものです。実装や運用ルール（StrategyModel.md、DataPlatform.md、DataSchema.md 等）についてはリポジトリ内の設計ドキュメントも併せて参照してください。必要であれば README を英語版に翻訳したり、各機能ごとの詳細使用例・運用手順（cron / CI / モニタリング）を追加で作成できます。