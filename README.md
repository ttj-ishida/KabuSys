# KabuSys

日本株向けの自動売買システム基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要な基盤機能群をまとめたライブラリです。主に以下をカバーします。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル）パイプラインと品質チェック
- RSS からのニュース収集（SSRF対策、トラッキング除去、冪等保存）
- マーケットカレンダー管理と営業日判定ユーティリティ
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ

設計上、冪等性（ON CONFLICT）、トレーサビリティ、セキュリティ（SSRF、XML攻撃対策）、および運用を意識したログ・エラー設計が盛り込まれています。

---

## 機能一覧

- データ取得
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - JPX マーケットカレンダー取得
- データ保存（DuckDB）
  - raw_prices / raw_financials / market_calendar / raw_news / ... のテーブル定義と初期化
- ETL
  - 差分更新（最終取得日からの差分）とバックフィル
  - 日次 ETL の統合実行（品質チェックオプションあり）
- 品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集
  - RSS 取得、URL 正規化、記事ID（SHA-256先頭32文字）生成、冪等挿入、銘柄紐付け
  - SSRF対策（リダイレクト検査・プライベートアドレス拒否）、XML攻撃対策（defusedxml）
- マーケットカレンダー管理
  - 営業日判定 / 前後営業日取得 / 期間内営業日取得 / 夜間バッチ更新ジョブ
- 監査ログ（audit）
  - signal_events, order_requests, executions 等の監査テーブルとインデックス

---

## 前提・依存関係

- Python 3.9+（タイプヒント等を使用）
- 主な Python ライブラリ:
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, datetime, logging 等を利用

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成することで自動読み込みされます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（config.Settings を参照）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知に使用（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルトあり:

- KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト "development"）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト "INFO"）

.env の自動読み込みルール:
- 読み込み順は OS 環境 > .env.local > .env
- .git または pyproject.toml を基準にプロジェクトルートを検出して読み込み
- テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（代表的なユースケース）

以下は Python REPL やスクリプト内で使う最小例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを自動作成
  ```

- 日次 ETL 実行（株価・財務・カレンダーを差分で取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())       # ETLResult の内容を確認
  ```

  run_daily_etl の主な引数:
  - target_date: ETL対象日（省略時は today）
  - id_token: J-Quants の id token を外部注入してテスト可能
  - run_quality_checks: 品質チェックの実行有無
  - backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 事前に保有する銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

  個別 API:
  - fetch_rss(url, source): 単一 RSS を取得して記事リストを返す
  - save_raw_news(conn, articles): raw_news に挿入（INSERT ... RETURNING で新規IDを返す）
  - save_news_symbols(conn, news_id, codes): 個別記事の銘柄紐付け

- マーケットカレンダー夜間更新（calendar_update_job）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- 監査ログスキーマ初期化（audit 用）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の id_token を明示的に取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

---

## 主要モジュールの説明（簡単）

- kabusys.config
  - 環境変数の読み込みと Settings オブジェクトを提供
  - .env / .env.local 自動読み込み・保護キー機能

- kabusys.data.jquants_client
  - J-Quants API への通信、レート制限、リトライ、ページネーション、DuckDB への保存関数を提供

- kabusys.data.schema
  - DuckDB の DDL を定義し init_schema() で全テーブルとインデックスを作成

- kabusys.data.pipeline
  - 差分取得ロジック、ETL 統合エントリポイント run_daily_etl を提供
  - 品質チェックを呼び出す (kabusys.data.quality)

- kabusys.data.news_collector
  - RSS 取得、XML パース、記事正規化、raw_news への保存、銘柄抽出と紐付け

- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ

- kabusys.data.audit
  - 監査ログ用スキーマと初期化ユーティリティ

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェックロジック

---

## 実運用上の注意

- J-Quants API のレート制限（120 req/min）に注意。jquants_client は固定間隔スロットリングで保護しますが、外部からの複数プロセス同時呼び出しなどでは注意が必要です。
- DuckDB のファイルパスは settings.duckdb_path で管理。ファイルのバックアップや同期方法を運用設計で決定してください。
- ニュース収集では外部 RSS にアクセスします。SSRF 対策や受信サイズ上限（デフォルト 10MB）を実装していますが、企業内運用ではプロキシ設定やネットワーク制御を検討してください。
- 監査ログ（audit）は削除しない前提で設計されています。保持ポリシーを運用で決定してください。
- 環境変数は機密情報を含むため `.env` を Git 管理しないでください。`.env.example` を用意して参照する運用を推奨します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                       — DuckDB スキーマ定義と初期化
    - jquants_client.py               — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                     — ETL パイプライン（差分更新、日次 ETL）
    - news_collector.py               — RSS ニュース収集・保存・紐付け
    - calendar_management.py          — マーケットカレンダー管理・営業日ロジック
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログスキーマと初期化
    - (その他: pipeline / audit 補助モジュール)
  - strategy/
    - __init__.py                     — 戦略層プレースホルダ
  - execution/
    - __init__.py                     — 発注/約定層プレースホルダ
  - monitoring/
    - __init__.py                     — 監視・メトリクスプレースホルダ

---

## テスト・デバッグ

- 各モジュールは id_token を外部から注入可能な形で設計されています（テストでのモックが容易）。
- news_collector._urlopen 等、一部内部関数はテスト用に差し替え可能です。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってオフにできます（CI やユニットテストで便利）。

---

質問や追加で欲しい README 内容（CI 設定例・Dockerfile・サンプル env.example・ユニットテスト例など）があれば教えてください。必要に応じて追記します。