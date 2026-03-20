# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants API からのデータ取得、DuckDB によるデータ格納、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、ETL パイプライン等を含むモジュール群を提供します。

---

## 概要

KabuSys は以下の機能を持つモジュール群で構成されたプロジェクトです。

- J-Quants API クライアント（データ取得・保存・認証・レート制御・リトライ）  
- DuckDB スキーマ定義・初期化機能（Raw / Processed / Feature / Execution 層）  
- ETL パイプライン（差分取得・バックフィル・品質チェック）  
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と探索ユーティリティ（IC・将来リターン）  
- 特徴量構築（Zスコア正規化・ユニバースフィルタ）  
- シグナル生成（コンポーネントスコア統合、BUY/SELL 生成、エグジット判定）  
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・XML安全パーサ・トラッキング除去）  
- マーケットカレンダー管理（営業日判定、next/prev/trading days）  
- 設定管理（.env 自動ロード、必須環境変数の検出）

設計方針としては「ルックアヘッドバイアスを避ける」「DB 保存は冪等」「外部依存を最小化（標準ライブラリ中心）」が掲げられています。

---

## 機能一覧

- data/jquants_client
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - RateLimiter、トークン自動リフレッシュ、リトライロジック
- data/schema
  - DuckDB テーブル定義と init_schema(db_path)
- data/pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の日次 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data/news_collector
  - fetch_rss, save_raw_news, extract_stock_codes, run_news_collection
  - SSRF 対策・gzip 制限・トラッキングパラメータ除去・ID は正規化 URL の SHA-256
- data/calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- config
  - 環境変数読み込み（.env/.env.local、自動ロードの可否フラグ）
  - Settings オブジェクト（必須トークン・DB パス・環境設定）

---

## 要件

- Python 3.10 以上を推奨
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
（プロジェクトの packaging / requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストールします（例）:

   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトに requirements.txt があれば:
   # pip install -r requirements.txt
   ```

3. パッケージを開発モードでインストール（任意）:

   ```bash
   pip install -e .
   ```

4. 環境変数 / .env を用意します。自動でプロジェクトルートの `.env` と `.env.local` が読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須の環境変数:

   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      (必須) — kabu ステーション API 用パスワード
   - SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID       (必須) — 通知先 Slack チャンネル ID

   オプション:

   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`（参考）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマを初期化します（デフォルトファイル path を使う場合）:

   Python REPL やスクリプトで:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # conn を使ってそのまま ETL / 検査等を実行できます
   ```

---

## 使い方（例）

以下は主要な処理を呼び出す例です。実運用ではロギング・エラーハンドリング・スケジューラ（cron / Airflow 等）でラップしてください。

- 日次 ETL を実行する

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 特徴量構築（strategy.feature_engineering.build_features）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features built: {n}")
  ```

- シグナル生成

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today())
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS から raw_news と news_symbols 作成）

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar records saved: {saved}")
  ```

---

## 注意点・運用メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）で行われます。テスト時などに自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB へは冪等に保存する設計（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）を意識しているため、再実行が安全です。
- J-Quants API のレート制限（120 req/min）に配慮した RateLimiter とリトライ実装があります。認証（id_token）は自動リフレッシュされます。
- ニュース収集では SSRF 対策、XML の安全パース、圧縮サイズ制限などを実装しており、記事 ID は正規化 URL のハッシュで冪等性を確保します。
- Strategy 層は発注 API（execution 層）に直接依存しない設計です。生成された signals テーブルを元に別層で発注処理を行う想定です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得/保存）
      - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       — 市場カレンダー管理
      - features.py                  — features の公開インターフェース
      - audit.py                     — 監査ログ用 DDL（signal_events 等）
    - research/
      - __init__.py
      - factor_research.py           — モメンタム/ボラティリティ/バリューの計算
      - feature_exploration.py       — 将来リターン/IC/summary 等
    - strategy/
      - __init__.py
      - feature_engineering.py       — 特徴量構築（正規化・ユニバースフィルタ）
      - signal_generator.py          — シグナル生成ロジック（final_score 等）
    - execution/                      — 発注/実行関連（プレースホルダ）
      - __init__.py
    - monitoring/                     — 監視・メトリクス収集（プレースホルダ）
      - __init__.py

---

## 開発・貢献

- コードはモジュール単位で分割されており、ユニットテストやモック注入（例: HTTP / urlopen / J-Quants レスポンス）を容易に行えるように設計されています。
- ETL・API 呼び出し部分は外部依存（ネットワーク）を分離しているため、ローカルでの回帰テスト時は id_token 注入や HTTP クライアントのモックを推奨します。

---

必要であれば README に「CLI 実行例」「CI 設定例」「推奨スケジューリング（cron/airflow）」や、より詳細な環境変数のサンプル (.env.example) を追加できます。どの範囲を追記したいか教えてください。