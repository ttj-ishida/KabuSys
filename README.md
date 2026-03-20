# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取り込み（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ/スキーマなど、戦略開発〜実行に必要なコンポーネントを備えています。

主な目的は「研究で得たファクターを安全にプロダクションに持ち込み、ルックアヘッドバイアスを避けつつ冪等にデータ保存・シグナル生成を行う」ことです。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得メソッド（settings オブジェクト）

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション・レート制御・リトライ）
  - DuckDB への冪等保存（ON CONFLICT で重複排除）
  - 保存ユーティリティ：save_daily_quotes / save_financial_statements / save_market_calendar

- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- データスキーマ管理
  - DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義（冪等）

- 特徴量計算（research / strategy）
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - features テーブルへ保存するための build_features

- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL の生成と signals テーブルへの冪等書込（generate_signals）
  - エグジット（ストップロス、スコア低下）の判定

- ニュース収集
  - RSS フィード取得・前処理・記事ID生成（URL 正規化→SHA-256）
  - SSRF / XML Bomb / 大きなレスポンス等に対する安全対策
  - raw_news / news_symbols への冪等保存、銘柄抽出ロジック

- カレンダー管理
  - market_calendar の更新ジョブ、営業日判定・前後営業日取得ユーティリティ

- 監査ログ
  - signal_events / order_requests / executions 等、トレーサビリティ用テーブル設計（UTC タイムスタンプ、冪等キー等）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型ヒントに union 型などを使用）
- DuckDB を使用（Python パッケージ `duckdb`）
- RSS の安全な XML パースに `defusedxml`

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください）

3. リポジトリをプロジェクトとしてインストール（任意）
   - pip install -e .

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行して DB を初期化して下さい。

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - メモリ DB を使う場合は db_path に ":memory:" を指定できます。

5. 環境変数設定（.env）
   - プロジェクトルートに `.env` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（少なくとも以下を設定する必要があります）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知が必要な場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - （任意）DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL

   - 簡単な .env 例:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development

---

## 使い方（サンプル）

以下は主要な API を使う最小サンプル例です。各関数は duckdb の接続オブジェクトを受け取るので、テストしやすく DI（依存注入）できます。

- スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日（営業日に調整）で実行
  print(result.to_dict())

- マーケットカレンダー更新（夜間バッチ）

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)

- 特徴量計算（build_features）

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2025, 1, 15))
  print(f"features upserted: {count}")

- シグナル生成（generate_signals）

  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, date(2025, 1, 15), threshold=0.6)
  print(f"total signals: {total_signals}")

- ニュース収集ジョブ

  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効銘柄コードの集合（例: {"7203","6758",...}）
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

注意点:
- すべての DB 書き込みは冪等性を意識して実装されています（ON CONFLICT 等）。
- run_daily_etl 内の品質チェックは、致命的な問題が見つかっても ETL を継続する設計です（呼び出し元で判断）。

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注機能利用時に必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

環境変数のロードはプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local の順で行われます。.env.local は .env を上書きするため、ローカルの秘密値を置くのに適しています。

---

## 主要モジュールと API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / duckdb_path / env / log_level / is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token (自動リフレッシュとリトライを内包)

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続を返す
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=None)

- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(conn, ...)

---

## ディレクトリ構成

（プロジェクトルートからの概観 — src/layout を基準）

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py                     # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得・保存）
      - news_collector.py           # RSS ニュース収集・保存
      - schema.py                   # DuckDB スキーマ定義・初期化
      - stats.py                    # 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      - features.py                 # features 用公開ラッパー
      - calendar_management.py      # market_calendar 関連ユーティリティ / バッチ
      - audit.py                    # 監査ログスキーマ（signal_events 等）
      - quality.py?                 # （品質チェックモジュール想定; コードベースに言及あり）
    - research/
      - __init__.py
      - factor_research.py          # momentum/volatility/value 計算
      - feature_exploration.py      # forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py      # build_features
      - signal_generator.py         # generate_signals
    - execution/                     # 発注 / 実行層（雛形・拡張点）
      - __init__.py
    - monitoring/                    # 監視・モニタリング用モジュール（想定）

---

## 開発・テストのヒント

- 自動環境読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - テストでは必要な環境変数を明示的にセットしてから settings をインポートしてください。

- DuckDB をインメモリで使うとユニットテストが簡単です（":memory:" を init_schema に渡す）。

- ネットワーク依存関数（jquants_client._request、news_collector._urlopen 等）はモック可能な設計（モジュールレベルの関数を差し替え）になっています。

- 重いジョブ（ETL、calendar_update_job、run_news_collection）はログを INFO/DEBUG にすると詳細が追えます。LOG_LEVEL 環境変数で制御できます。

---

## 留意点 / 設計方針（抜粋）

- ルックアヘッドバイアス回避: 特徴量計算・シグナル生成は target_date 時点のデータのみを使用するよう設計されています。
- 冪等性: DB 書き込みは可能な限り冪等に（ON CONFLICT / INSERT ... DO UPDATE / INSERT ... DO NOTHING）実装されています。
- セキュリティ: RSS 収集での SSRF 対策、XML パース時の defusedxml 利用、大きなレスポンス制限などを実装。
- レート制御: J-Quants API のレート上限を守るためスロットリング・リトライ・トークン自動再取得を実装しています。

---

必要があれば README に以下を追加できます:
- より詳細な .env.example（テンプレート）
- CI / デプロイ手順（systemd / cron / Airflow 等での定期実行例）
- テーブル定義（DataSchema.md などの抜粋）
- API レスポンス例やシグナル生成の数学的仕様（StrategyModel.md 抜粋）

他に追加したい情報（例: .env.example の完全版、実運用上の注意点、テストケース例など）があれば教えてください。