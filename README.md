# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）です。  
データ収集（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の層で構成されたシステムのコア実装を含みます。

- Data layer: J-Quants API からのデータ取得、RSS ニュース収集、DuckDB による永続化
- Processed/Feature layer: 日次株価整形、ファクター計算、Zスコア正規化、features / ai_scores テーブル
- Strategy layer: 特徴量を統合してシグナル（BUY/SELL）を生成
- Execution/Audit: 発注・約定・ポジション管理用スキーマ（監査ログ含む）
- Research utilities: ファクター探索・IC 計算などの研究向けユーティリティ

設計方針のハイライト:
- 冪等性（DB への保存は ON CONFLICT や UPSERT）を重視
- ルックアヘッドバイアスを防ぐため、target_date 時点のデータのみを使用
- 外部依存は最小限（標準ライブラリ + duckdb, defusedxml など）
- API 呼び出しはレート制御・リトライ・トークン自動リフレッシュ対応

---

## 主な機能一覧

- J-Quants クライアント（jquants_client）
  - 日足・財務・マーケットカレンダーの取得（ページネーション対応）
  - リトライ・レートリミット・401 リフレッシュ対応
  - DuckDB へ冪等保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）
- ETL パイプライン（data.pipeline）
  - 差分取得（バックフィル対応）、保存、品質チェック、日次 ETL 実行 run_daily_etl
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義・初期化 init_schema / get_connection
- ニュース収集（data.news_collector）
  - RSS 取得、SSRF 対策、前処理、raw_news 保存、銘柄抽出・紐付け
- 研究用ファクター計算（research.factor_research）
  - Momentum / Volatility / Value の計算（prices_daily / raw_financials を利用）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
- 汎用統計ユーティリティ（data.stats）
  - zscore_normalize など
- マーケットカレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等のスキーマ定義（監査用）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントや記法に依存）
- pip が利用可能

1. リポジトリをクローン（既にソースがある場合は不要）

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （パッケージ管理ファイルがある場合はそちらに従ってください）

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須環境変数（コード内で _require を使用）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オートロード順序: OS 環境 > .env.local > .env（.env.local は .env の上書き）

5. DuckDB スキーマ初期化
   - Python から実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - :memory: を使えばインメモリ DB で動作確認できます:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 基本的な使い方（例）

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（target_date の features を生成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, date(2025, 1, 31))
  print(f"upserted features: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total_signals = generate_signals(conn, date(2025, 1, 31))
  print(f"signals generated: {total_signals}")
  ```

- ニュース収集ジョブ（RSS から raw_news を保存）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄一覧（例: {'7203', '6758', ...}）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  print(res)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意:
- 上記例では DuckDB 接続を直接使っています。運用環境では接続管理やエラーハンドリングを適切に実装してください。
- J-Quants API を利用する処理は認証トークンが必須です。トークン管理は Settings 経由で行われます。

---

## 環境変数一覧（概要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下の主なファイル群）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py         — RSS ニュース収集・前処理・DB 保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — 市場カレンダー管理
    - audit.py                  — 監査ログスキーマ（signal_events, executions 等）
    - features.py               — features 用公開ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        — Momentum/Volatility/Value 計算
    - feature_exploration.py    — 将来リターン、IC、統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py    — 生ファクターの正規化と features 保存
    - signal_generator.py       — final_score 計算と signals 生成
  - execution/                  — 発注・実行ロジック用パッケージ（未実装/空）
  - monitoring/                 — 監視・メトリクス用（未実装/空）

---

## 開発・貢献メモ

- DuckDB を使用しているため、クエリや大規模データ処理は比較的高速です。スキーマは DataSchema.md の仕様に基づいて実装されています（ドキュメント参照推奨）。
- ニュース収集は defusedxml を利用して XML 攻撃対策を行っています。
- API リクエストは固定間隔の RateLimiter と指数バックオフリトライを備えています。
- 追加機能やバグフィックスの貢献歓迎。pull request の際はテストと簡単な使用例を添えてください。

---

## ライセンス / 免責

このリポジトリはプロジェクトの一部実装を示すサンプルです。実運用に使用する前に十分な監査・テストを行ってください。金融取引に伴うリスクは利用者の責任です。

---

必要であれば、この README を英語版に翻訳したり、各モジュールの使い方（関数別の詳細な API リファレンス）を追加で作成します。どのドキュメントを優先するか指示してください。