# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（ライブラリ層）。  
J-Quants / DuckDB を用いたデータ取り込み（ETL）、品質チェック、監査ログ（発注→約定トレース）などの基盤機能を提供します。

主な設計方針：
- データ層を Raw / Processed / Feature / Execution の多層で構成
- J-Quants API 呼び出しはレート制限・リトライ・トークン自動リフレッシュを考慮
- DuckDB を用いた冪等な保存（ON CONFLICT DO UPDATE）
- 品質チェックでデータ異常を検出し、呼び出し側で対処可能にする
- 発注〜約定の監査トレーサビリティを UUID 階層で保証

---

## 機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（Settings）
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得日時（fetched_at）を UTC で記録
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 各層のテーブル定義とインデックス
  - スキーマ初期化（冪等）
- ETL パイプライン
  - 差分取得（最終取得日から backfill を含めて再取得）
  - 保存（冪等）、品質チェックの実行
  - 日次 ETL のエントリポイント（run_daily_etl）
- 品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合 等のチェック
  - 各問題は QualityIssue オブジェクトとして返却（severity を含む）
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルを提供
  - 発注フローの完全トレースを目的としたスキーマとインデックス

---

## 要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
- （任意）J-Quants API の利用には J-Quants の資格情報が必要

※ 依存はプロジェクト側の pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   - 例（Unix 系）:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -U pip

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb
     - pip install -e .    # パッケージとして利用する場合（開発インストール）

3. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を配置すると自動読み込みされます。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuAPI ベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - 自動 .env 読み込みを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化できます（下例参照）。

---

## 使い方（簡易サンプル）

- 基本的な DB 初期化と日次 ETL の実行例:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.pipeline import run_daily_etl

  # DuckDB を初期化して接続を取得（デフォルトパスは settings.duckdb_path）
  conn = init_schema(settings.duckdb_path)

  # 監査テーブルを追加する（省略可能）
  init_audit_schema(conn)

  # 日次 ETL を実行（target_date を指定しなければ今日が対象）
  result = run_daily_etl(conn)

  # 結果確認
  print(result.to_dict())
  ```

- J-Quants API を直接使ってデータ取得する例:

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- 個別 ETL ジョブの実行（価格データだけ等）:

  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- 品質チェックだけ実行する例:

  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

---

## 環境変数 / .env の注意点
- パッケージ初期化時に .env/.env.local を自動で読み込みます（プロジェクトルート検出に基づく）。
- .env の書式は一般的な KEY=VALUE に加え、export KEY=VALUE やシングル／ダブルクォート、エスケープにも対応します。
- テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数管理、自動 .env 読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ、レートリミット／リトライ）
    - schema.py
      - DuckDB のスキーマ定義と初期化（raw/processed/feature/execution）
    - pipeline.py
      - ETL パイプライン（差分取得・保存・品質チェック／run_daily_etl 等）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 発注・約定の監査テーブル初期化（signal_events, order_requests, executions）
    - (他: pipeline, audit と連携する補助モジュール)
  - strategy/
    - __init__.py （戦略層のエントリ、実装はプロジェクト側で拡張）
  - execution/
    - __init__.py （発注・ブローカー接続層のためのプレースホルダ）
  - monitoring/
    - __init__.py （監視／メトリクス系のためのプレースホルダ）

---

## 設計上のポイント（開発者向けメモ）
- J-Quants クライアントはページネーション鍵を使って全件を取得、ページ間で同一 ID トークンを共有しているため、get_id_token の自動リフレッシュに注意（allow_refresh フラグあり）。
- DuckDB のテーブル作成は冪等（CREATE TABLE IF NOT EXISTS）で安全。初回は init_schema を実行してください。
- ETL は Fail-Fast ではなく、各ステップでエラーを収集して継続する設計（呼び出し元で対応を決定）。
- 監査ログは削除しない前提で FK とインデックスを設計。UTC タイムゾーンを利用しています。

---

## トラブルシュート
- .env が読み込まれない／環境変数が未設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルート（.git / pyproject.toml）が正しく検出されるディレクトリ構成か確認
  - 必須環境変数が不足していると settings のプロパティで ValueError が発生します
- J-Quants API 呼び出しで 401 が返る:
  - get_id_token が自動でリフレッシュするが、refresh token（JQUANTS_REFRESH_TOKEN）が正しいか確認
- DuckDB にテーブルがない:
  - init_schema を呼んでスキーマ初期化してください

---

必要であれば、.env.example のテンプレートや運用用の systemd / cron 設定、より具体的なコード例（監視通知・発注フロー）も作成できます。どの情報が欲しいか教えてください。