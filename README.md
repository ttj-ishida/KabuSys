# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
DuckDB をデータレイヤに使い、J-Quants からマーケットデータを取得して ETL → 特徴量生成 → シグナル生成 → 発注（Execution 層）へ接続するためのモジュール群を提供します。研究（research）用ユーティリティやニュース収集、監査ログ（audit）など運用に必要な要素も含まれています。

バージョン: 0.1.0

## 主な特徴（機能一覧）
- データ取得（J-Quants API）と保存
  - 株価日足、財務データ、JPX カレンダーの取得（ページネーション・リトライ・トークン自動リフレッシュ対応）
  - レート制限管理（120 req/min）
- DuckDB スキーマ定義と初期化（冪等）
  - Raw / Processed / Feature / Execution 層を含むスキーマ
- ETL パイプライン
  - 差分フェッチ、バックフィル、品質チェック（quality モジュール経由）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、記事保存、銘柄抽出・紐付け
  - SSRF 対策、XML パース安全化（defusedxml）
- 研究用ファクター計算 / 特徴量生成
  - Momentum / Volatility / Value 等のファクター計算（research/factor_research）
  - Z スコア正規化ユーティリティ（data.stats）
  - 特徴量の生成と features テーブルへの保存（strategy/feature_engineering）
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成（strategy/signal_generator）
  - Bear レジーム抑制、ストップロス等のエグジット判定
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions）設計（audit モジュール）
- 環境変数管理（.env 自動読み込み機能）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部に型注釈を使用）を推奨
- pip が利用可能

1. リポジトリをクローン／配置
   - 例: git clone ... またはソースを配置

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .\.venv\Scripts\activate   (Windows)

3. 依存パッケージをインストール
   - 主要依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発用にパッケージとしてインストールする場合:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須項目（最低限）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
   - オプション:
     - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
     - LOG_LEVEL=DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を指定すればインメモリ DB で初期化できます（テスト用）。

---

## 使い方（基本的なワークフロー例）

ここでは代表的な操作の流れを示します（ETL → 特徴量生成 → シグナル生成）。

1. DB 接続・初期化（初回のみ）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL（J-Quants からデータ取得して保存）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェック の順で処理します。
   - id_token を外部で取得して渡すことも可能（テスト用）。

3. 特徴量の計算（features テーブルの構築）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

   - build_features は research モジュールのファクター計算を呼び出して正規化・クリップし、features テーブルへ日付単位で置換（冪等）します。

4. シグナル生成（signals テーブルへの書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals

   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")
   ```

   - generate_signals は ai_scores や features を参照して final_score を計算し、BUY / SELL シグナルを signals テーブルへ保存します。
   - 重み（weights）を引数で上書き可能。Bear レジームでは BUY を抑制。

5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. J-Quants クライアントの直接利用例
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes

   recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境変数ベースの設定アクセス（jquants_refresh_token, duckdb_path, env 等）
  - .env の自動読み込み機能（プロジェクトルートを探索）

- kabusys.data
  - jquants_client
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存）
    - レート制限・リトライ・トークン自動更新付き
  - schema
    - init_schema(db_path), get_connection(db_path)
    - スキーマ定義（Raw/Processed/Feature/Execution 層）
  - pipeline
    - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector
    - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
  - calendar_management
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - stats
    - zscore_normalize

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

## 実運用上の留意点
- 環境変数管理:
  - OS 環境変数が優先され、.env/.env.local は自動でロードされます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ:
  - news_collector は SSRF 対策、XML パース安全化（defusedxml）、受信サイズ制限を実装しています。
  - J-Quants クライアントは 401 受信時にリフレッシュを試行します（1 回のみ）。
- 冪等性:
  - 多くの保存関数は ON CONFLICT / DO UPDATE / DO NOTHING を用いて冪等に動作します。
- テスト:
  - 各ネットワーク呼び出し部分（例: _urlopen）をモック可能な設計になっており、ユニットテストの差し替えが容易です。

---

## ディレクトリ構成

概略（主要ファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - (quality.py 等が別途存在する想定)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (モニタリング関連モジュール用ディレクトリ)

各モジュールの責務:
- data: データ取得・保存・ETL・カレンダー・ニュース等
- research: ファクター計算・探索的解析
- strategy: 特徴量変換・シグナル生成
- execution: 発注・約定連携（インタフェース層）
- monitoring: 運用監視・アラート

---

## 付録: よく使う関数サンプル（要点まとめ）
- DB 初期化:
  - init_schema(settings.duckdb_path)
- ETL 実行:
  - run_daily_etl(conn, target_date)
- 特徴量構築:
  - build_features(conn, target_date)
- シグナル生成:
  - generate_signals(conn, target_date, threshold=0.6)

---

問題・要望・機能拡張の提案があれば README を更新します。必要であれば、具体的な実行スクリプト例（cron 用や Dockerfile、CI ワークフローなど）も追加で作成できます。どの形式を優先しますか？