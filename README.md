# KabuSys

日本株自動売買基盤（KabuSys）のリポジトリ向け README（日本語）

概要、機能一覧、セットアップ、使い方、ディレクトリ構成をまとめています。  
このプロジェクトは J-Quants API を利用したデータ取得、DuckDB によるデータ保管、特徴量作成・シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む日本株量化運用基盤のコアモジュール群です。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームのコアライブラリ群です。主な目的は次の通りです：

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution レイヤ）
- 研究（research）で作成したファクターを戦略用の特徴量へ変換し、戦略シグナルを生成
- RSS フィードに基づくニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定など）
- ETL パイプライン（差分更新・品質チェック）
- 発注・約定・監査ログのためのスキーマ設計（実行層は別モジュールで実装）

設計上の方針として、ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）、冪等性（ON CONFLICT 等による上書き）、外部 API への過負荷対策（レート制御・バッファリング）を重視しています。

---

## 主な機能（抜粋）

- data
  - J-Quants API クライアント（fetch/save/ページネーション/リトライ/自動トークン更新）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ニュース収集（RSS -> raw_news、記事ID正規化、銘柄抽出、SSRF対策）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - 統計ユーティリティ（zscore_normalize）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（将来リターン calc_forward_returns、IC calc_ic、統計 summary）
- strategy
  - 特徴量構築（build_features: raw factor を正規化して features テーブルへ）
  - シグナル生成（generate_signals: features + ai_scores を統合して BUY/SELL を作成）
- execution / monitoring / audit
  - スキーマ上での実行層テーブル・監査ログ設計（order_requests, executions, signal_events 等）
- config
  - 環境変数管理（.env 自動読み込み、必須キー検証、KABUSYS_ENV/LOG_LEVEL 判定）

---

## セットアップ手順

前提
- Python 3.9+（タイプヒントで | を使っているため 3.10+ を推奨）
- pip が利用可能

1. リポジトリをクローン
   - (例) git clone <repo-url>

2. 開発用依存のインストール（最低限）
   ```
   python -m pip install -e .
   python -m pip install duckdb defusedxml
   ```
   ※ packaging / extras が用意されていれば `pip install -e ".[dev]"` 等を利用してください。

3. 環境変数 (.env) の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（config モジュールによる自動ロード）。  
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。
   - 必須環境変数（Settings クラス参照）
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - 任意（デフォルトあり）
     - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

   例 `.env`（実際のトークンは安全に管理してください）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   Python REPL かスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # defaults to data/kabusys.duckdb
   ```
   これで必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な操作例）

以下はライブラリを直接呼び出す例です。実運用では適切なスクリプト／ジョブ定義を作成して Cron / Airflow 等で実行します。

- ETL（日次）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（feature layer へ保存）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes には既知の銘柄コードセットを渡すと記事と銘柄の紐付けを行います
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からのデータ取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

注意点:
- run_daily_etl 等は内部で品質チェックモジュールを呼びます。品質問題は ETLResult の quality_issues に格納されます（致命的エラーがあれば errors に追加されます）。
- generate_signals は AI スコア（ai_scores テーブル）を参照しますが、未登録の場合は中立値で補完されます。
- build_features / generate_signals は target_date 時点のデータのみを用いることでルックアヘッドバイアスを防止します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

config.Settings クラスで必須チェックが行われます（未設定時は ValueError）。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（fetch/save）
      - news_collector.py             — RSS ニュース収集 & 保存
      - schema.py                     — DuckDB スキーマ定義 / init_schema
      - stats.py                      — zscore_normalize など統計ユーティリティ
      - pipeline.py                   — ETL パイプライン（run_daily_etl など）
      - calendar_management.py        — カレンダー管理 / calendar_update_job
      - audit.py                      — 監査ログスキーマ定義
      - features.py                   — 公開インターフェース（zscore 再エクスポート）
      - execution/                     — 実行層（発注等）用パッケージ（空 __init__ あり）
    - research/
      - __init__.py
      - factor_research.py            — モメンタム・ボラティリティ・バリュー等
      - feature_exploration.py        — 将来リターン / IC / summary
    - strategy/
      - __init__.py                   — build_features, generate_signals を再エクスポート
      - feature_engineering.py        — features テーブル構築
      - signal_generator.py           — signals テーブル生成ロジック
    - execution/                       — 発注実装領域（モジュール化済）
    - monitoring/                      — 監視 / metric / アラート関連（未表示の実装領域）
- pyproject.toml / setup.cfg 等（配布設定があればルートに存在）

（上記は主要なファイルを抜粋したものです。実際のツリーはリポジトリの内容に従ってください）

---

## テスト・開発時のヒント

- 自動 .env 読み込みは config モジュール実行時に行われます。テスト内で環境を明示的に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で os.environ をパッチしてください。
- DuckDB のテストでは `":memory:"` を init_schema に渡すとインメモリ DB が利用できます。
- ネットワーク呼び出しを伴うモジュール（jquants_client, news_collector）については HTTP 呼び出しをモックすることで単体テストが容易になります。コード中にモック可能な呼び出し箇所（例: _urlopen や _request 等）が用意されています。

---

## 運用上の注意

- J-Quants の API にはレート制限があるため、jquants_client は固定間隔スロットリングとリトライロジックを含みます。外部からの連続大量要求は避けてください。
- production での発注（execution 層）を有効にする際は KABUSYS_ENV を適切に `live` に設定し、発注ロジックとブローカ接続の安全性（冪等性・監査・失敗時のリカバリ）を十分に検証してください。
- 機密情報（トークンやパスワード）は `.env` を含めてバージョン管理しないでください。Vault 等のシークレット管理を推奨します。

---

必要であれば README に「クイックスタート用スクリプト」や「運用フロー図（ETL→Feature→Signal→Execution）」、サンプル .env.example の追記も作成できます。追加で欲しいセクションや具体的なコマンド例（systemd / cron / Airflow でのジョブ定義サンプルなど）があれば教えてください。