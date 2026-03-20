# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、DuckDBベースのデータレイヤ、特徴量計算、シグナル生成、ニュース収集、監査ログなどを含んだモジュール群を提供します。

主に研究（research）→ データパイプライン（data）→ 戦略（strategy）→ 実行（execution）へとつながるワークフローを想定しています。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制限・リトライ・トークン自動リフレッシュを内蔵
- データ基盤（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化（冪等）
  - ETLパイプライン（差分取得・バックフィル・品質チェック）
- 特徴量（feature）算出
  - Momentum / Volatility / Value 等のファクター計算
  - Zスコア正規化・ユニバースフィルタ適用・features テーブルへの UPSERT
- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を算出
  - Bear レジーム検知による BUY 抑制、SELL（エグジット）ルール
  - signals テーブルへ冪等的に書き込み
- ニュース収集
  - RSS フィードから記事を取得・前処理・raw_news 保存・銘柄抽出の紐付け
  - SSRF 防御・XML の安全パース・受信サイズ制限
- カレンダー管理
  - JPXマーケットカレンダーの差分取得・営業日判定ユーティリティ
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions などの監査テーブル定義
- 研究用ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Zスコア正規化

---

## 前提（Prerequisites）

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants / RSS フィード）
- 環境変数（下記参照）

※ パッケージ管理はプロジェクト側の要件に合わせて `pip` / `poetry` 等で設定してください。

---

## セットアップ手順（Quickstart）

1. リポジトリをクローンして開発インストール（例）
   - pip を使う場合:
     - pip install -e .
   - poetry を使う場合は pyproject.toml に従ってください。

2. 必要パッケージをインストール
   - 例: pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートの `.env` / `.env.local` を用意すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 必須の環境変数（Settings により参照・必須判定されるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python から初期化:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すことでインメモリ DB を使用できます（テスト時などに便利）。

---

## 使い方（主要なユースケース）

以下はライブラリを直接インポートして使う最小例です。実運用ではログ設定・エラーハンドリング・スケジューリング等が必要です。

- ETL（日次データ取得）
  ```
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量のビルド（features テーブルへ書き込み）
  ```
  from datetime import date
  from kabusys.strategy import build_features
  # conn は duckdb 接続（init_schema の戻り値等）
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 有効銘柄コードの集合（銘柄抽出で使用）
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(results)  # {source_name: saved_count}
  ```

- カレンダー更新バッチ
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からのデータ取得例（低レベル）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 重要な設計ノート・運用上の注意

- 環境変数自動ロード:
  - .env と .env.local を自動でプロジェクトルートから読み込みます（ただし OS環境変数が優先）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 冪等性:
  - データ保存は ON CONFLICT / UPSERT を活用して冪等に設計されています。
- Look-ahead バイアス対策:
  - 特徴量・シグナル生成は target_date 時点までのデータのみを使用する設計になっています。
  - J-Quants データ取得時は fetched_at を UTC で記録します。
- レート制限・リトライ:
  - J-Quants クライアントは 120 req/min のレート制限、指数バックオフによるリトライ、401 時のトークンリフレッシュを備えています。
- ニュース収集の安全対策:
  - RSS の XML パースは defusedxml を使用し、SSRF 対策や受信サイズ制限（10MB）を実装しています。

---

## 主要 API（関数・モジュールの概観）

- kabusys.config
  - settings: 環境変数経由の設定アクセス（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema, get_connection
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.stats
  - zscore_normalize
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

---

## ディレクトリ構成

プロジェクトの主要ファイル・フォルダの構成例（src/kabusys 以下）:

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
      - (その他 data 関連モジュール)
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
    - monitoring/  (存在を __all__ に含めているが、実装は別途)
    - (その他トップレベルモジュール)

---

## 開発・テスト

- 単体テストや CI はリポジトリの設定に依存します。DuckDB のインメモリ接続（":memory:"）を使うとテストが容易です。
- ネットワーク周りはモック化してテストを行ってください（jquants_client._request, news_collector._urlopen などはテスト時に差し替え可能）。

---

## ライセンス・貢献

リポジトリに LICENSE ファイルがあればそちらを参照してください。バグ報告・機能提案は Issue を作成してください。

---

以上。README の内容に追記したい項目（例: CI 設定、requirements.txt、運用手順、Slack 通知の例など）があれば教えてください。