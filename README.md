# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ライブラリ本体）。  
データ取得（J-Quants）、ETL、データ品質チェック、DuckDBスキーマ、監査ログなどの基盤機能を提供します。

## 概要

KabuSys は以下を目的とした内部用ライブラリです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得
- DuckDB に対するスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント：
- API レート制限（120 req/min）への配慮（モジュール内 RateLimiter）
- リトライ・トークン自動リフレッシュ（401 を受けた際にリフレッシュして再試行）
- ETL の冪等性（DuckDB への INSERT は ON CONFLICT DO UPDATE）
- 品質チェックは全件収集型（Fail-Fast ではない）

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（fetch/save 関数、ページネーション、トークン管理、リトライ）
- data.schema: DuckDB 用スキーマ定義と初期化関数（init_schema / get_connection）
- data.pipeline: 日次 ETL（差分更新、バックフィル、カレンダー先読み、品質チェック）
- data.quality: データ品質チェック群（欠損、スパイク、重複、日付整合性）
- data.audit: 監査ログ用スキーマ & 初期化（signal_events / order_requests / executions）
- config: 環境変数管理（.env 自動ロード、必須変数チェック、環境切替）

## セットアップ手順

前提:
- Python 3.10+（typing | 型注釈の使用があるため近年の Python を推奨）
- duckdb（DuckDB Python パッケージ）

1. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   プロジェクトに requirements.txt がある場合:
   ```
   pip install -r requirements.txt
   ```
   単体利用なら最低限 duckdb をインストール:
   ```
   pip install duckdb
   ```

3. リポジトリを editable モードでインストール（開発時）
   ```
   pip install -e .
   ```

## 環境変数（.env）

KabuSys はプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数 > .env.local > .env の優先度）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN        : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）

任意/設定例:
- KABUSYS_ENV            : `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL              : `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: .env のパースはコメント、クォート、エスケープ、`export KEY=val` 形式に対応しています。

## 使い方（基本例）

以下はライブラリを使って DuckDB のスキーマを初期化し、日次 ETL を実行する最小例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data import schema

   # ファイル DB を作成してスキーマを初期化
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. 監査ログスキーマを追加（必要に応じて）
   ```python
   from kabusys.data import audit

   audit.init_audit_schema(conn)
   ```

3. 日次 ETL を実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # 実行（戻り値は ETLResult）
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

4. 品質チェック単体実行
   ```python
   from kabusys.data import quality
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn, target_date=date.today())
   for i in issues:
       print(i)
   ```

5. J-Quants の個別取得（テストや詳細利用）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

   token = get_id_token()  # settings から refresh token を取得して id_token を作る
   records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
   ```

注記:
- jquants_client はリトライと 401 時の自動リフレッシュ、モジュールレベルでの id_token キャッシュを持っています。
- ETL 関数は id_token を引数で注入可能（テスト容易性のため）。

## API（主な公開関数 / クラス）

- kabusys.config.settings — 環境設定アクセス（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env）
- kabusys.data.schema.init_schema(db_path) -> duckdb connection
- kabusys.data.schema.get_connection(db_path) -> duckdb connection
- kabusys.data.jquants_client.get_id_token(refresh_token=None) -> id_token
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.quality.run_all_checks(conn, target_date=None, ...)
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)

## ディレクトリ構成

（リポジトリの主要ファイル／ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ・初期化
    - pipeline.py
  - strategy/                — 戦略モジュール用パッケージ（プレースホルダ）
  - execution/               — 発注実行層パッケージ（プレースホルダ）
  - monitoring/              — 監視モジュール（プレースホルダ）

主要なソースは上記の通りで、strategy / execution / monitoring は現在パッケージ初期化のみ（拡張ポイント）です。

## 開発メモ / 実装上のポイント

- .env はプロジェクトルート（.git または pyproject.toml を基準）から自動で読み込まれます。テスト時などで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API は 120 req/min 制限があるため内部で固定間隔の RateLimiter を実装しています（最小間隔 0.5 秒）。
- jquants_client の _request は 408/429/5xx に対し指数バックオフで最大 3 回リトライします。401 はトークンをリフレッシュして 1 回リトライします。
- DuckDB スキーマのテーブル作成は冪等（CREATE IF NOT EXISTS）なので再初期化しても安全です。
- ETL は各ステップを独立して例外処理するため、1 ステップ失敗でも他のステップを継続します。結果は ETLResult に集計されます。

## よくある操作（コマンド例）

- スキーマ初期化（Python スクリプトを用意して実行）:
  ```bash
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
  ```

- 日次 ETL をスケジューラ（cron 等）から呼ぶ:
  1. 仮想環境を有効化
  2. スクリプトを作成して run_daily_etl を呼ぶ
  3. ログ・結果を Slack 等に通知（別モジュールで実装）

## 免責・今後の拡張

このリポジトリはバックエンド基盤（データ面・監査面）を提供します。注文実行・取引所連携・戦略ロジックは別モジュールとして実装・統合してください。将来的に次を想定しています：

- 実ブローカー接続・約定処理の実装（kabu API ラッパー）
- 戦略フレームワークとポートフォリオ最適化
- モニタリング・アラート機能（Prometheus / Grafana など）

もし README に追記してほしい例（CI、テストの実行方法、依存パッケージの完全な一覧、サンプル .env.example 等）があれば指示してください。