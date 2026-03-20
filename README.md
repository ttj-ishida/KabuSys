# KabuSys

日本株自動売買システムのライブラリ群。データ取得（J-Quants）、ETL、DuckDBスキーマ管理、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等を含むモジュール群を提供します。

主に研究環境（factor research / feature exploration）と本番／ペーパートレード環境（execution / audit / orders など）双方を支援する設計になっています。

---

## 概要

KabuSys は次の要素で構成される日本株向けの自動売買基盤ライブラリです。

- J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
- ETL パイプライン（差分取得・バックフィル、品質チェックとの連携）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 特徴量エンジニアリング（research の生ファクターを統合・正規化）
- シグナル生成（正規化済み特徴量 + AI スコア → final_score → BUY/SELL）
- ニュース収集（RSS フィード、SSRF対策、URL正規化、銘柄抽出）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 設定管理（.env / 環境変数の自動ロード）

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「外部API呼び出しの安全化（SSRF対策等）」を重視しています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - 環境変数 / .env の読み込み、自動ロード（プロジェクトルート検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- kabusys.data
  - jquants_client: J-Quants からのデータ取得（株価、財務、カレンダー）と DuckDB への保存（冪等）
  - schema: DuckDB のテーブル定義と init_schema()
  - pipeline: 差分ETL / 日次 ETL 実行（run_daily_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存、銘柄抽出
  - calendar_management: 営業日判定、calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.research
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー

- kabusys.strategy
  - feature_engineering.build_features: features テーブルの構築（正規化・フィルタ）
  - signal_generator.generate_signals: features + ai_scores → signals の書き込み（BUY/SELL）

- kabusys.execution / kabusys.monitoring / kabusys.audit
  - execution 層・監査ログ等（スキーマ定義、監査用DDL 等を含む）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリ_URL>
   cd <repo>

2. Python 仮想環境作成（任意だが推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   プロジェクトの `pyproject.toml` / `requirements.txt` があればそれに従ってください。最低限必要な主なパッケージ（例）:
   - duckdb
   - defusedxml

   例（最小）:
   pip install duckdb defusedxml

   開発パッケージやその他はプロジェクトの依存ファイルをご参照ください。

4. 環境変数の設定

   プロジェクトルートに `.env`（と必要なら `.env.local`）を作成します。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベースURL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   自動ロードを無効化したい場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   `.env` の例:

   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化

   Python で以下を実行してスキーマを作成します（ファイルパスは環境変数で指定した DUCKDB_PATH を使用することを推奨）:

   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

---

## 使い方（主要な操作例）

以下はライブラリをプログラムから利用する際の基本的な呼び出し例です。

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェックを含む）:

  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量を構築する（DuckDB 接続と対象日を渡す）:

  from kabusys.strategy import build_features
  from datetime import date
  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, date(2024, 1, 10))
  print(f"features upserted: {n}")

- シグナルを生成する:

  from kabusys.strategy import generate_signals
  from datetime import date
  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals written: {total}")

- RSS ニュース収集と保存:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（バッチ）:

  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- J-Quants API からの直接取得（デバッグ用）:

  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  print(len(quotes))

備考:
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取るよう設計されています。init_schema() はスキーマ作成後の接続を返しますが、get_connection() で既存 DB に接続可能です。
- run_daily_etl 等の上位処理は内部で例外処理を行い、可能な限り他のステップを続行します。戻り値（ETLResult）にエラーや品質問題が記録されます。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（検証済み値のみ）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は `1` を設定

config.Settings クラス経由で安全に取得できます（環境変数未設定時は ValueError を送出する必須項目があります）。

---

## ディレクトリ構成

主要なファイル/モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他: quality.py 等が想定される)
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
  - monitoring/
    - (監視/メトリクス用モジュール)

（上記はソース内の主要ファイルを抜粋したものです。実際のリポジトリでは追加のモジュールやテスト・ユーティリティ等が存在する可能性があります。）

簡易ツリー例:

src/
├─ kabusys/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ data/
│  │  ├─ jquants_client.py
│  │  ├─ news_collector.py
│  │  ├─ pipeline.py
│  │  ├─ schema.py
│  │  └─ ...
│  ├─ research/
│  │  ├─ factor_research.py
│  │  └─ feature_exploration.py
│  ├─ strategy/
│  │  ├─ feature_engineering.py
│  │  └─ signal_generator.py
│  └─ execution/
│     └─ __init__.py

---

## 運用上の注意 / ベストプラクティス

- DuckDB ファイルは定期的にバックアップしてください（特に本番環境）。
- 環境変数（トークン/パスワード）は安全に管理してください（Vault 等の利用を推奨）。
- J-Quants の API レート制限を尊重するため、jquants_client は内部でレート制御とリトライを行います。直接の多数同時リクエストは避けてください。
- news_collector は外部 RSS を取得します。SSRF 対策・レスポンスサイズ制限が組み込まれていますが、外部URLの扱いには注意してください。
- run_daily_etl 等のバッチはログと戻り値（ETLResult）を監視し、品質問題が検出された場合は原因を調査の上対応してください。
- KABUSYS_ENV を適切に設定し（development / paper_trading / live）、生成されたシグナルや実際の発注処理を環境に応じて切り替えてください。

---

必要があれば、README に以下を追加できます：
- 依存パッケージの厳密なバージョン一覧（requirements.txt や pyproject.toml から）
- CI / テスト実行方法
- デプロイ手順（cron / Airflow / CIスケジュール）
- よくあるトラブルシュート集

追加したい項目があれば指示してください。