# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（プロトタイプ）
（パッケージ名: `kabusys`）

このリポジトリは、データ取得・ETL・品質チェック・監査ログ・スキーマ定義など、
自動売買システムのデータ基盤・監査基盤の核となるモジュール群を含んでいます。

主な設計方針：
- J-Quants API 等からのデータ取得を行い、DuckDB に冪等的に格納する
- ETL は差分更新・バックフィルを考慮し、品質チェックを行う
- 発注〜約定の監査ログは UUID 連鎖でトレース可能に保存する
- API レート制限・リトライ・トークン自動更新等を備える

---

## 主要な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー取得）
  - レート制限（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）をサポートする保存関数

- data/schema.py
  - DuckDB 向けのスキーマ定義（Raw / Processed / Feature / Execution 層）
  - テーブル作成・インデックス作成を行う `init_schema()`、既存 DB への接続取得 `get_connection()`

- data/pipeline.py
  - 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - 取得範囲の自動算出、バックフィル、カレンダー先読み機能
  - `run_daily_etl()` により一括処理と品質チェックの実行

- data/quality.py
  - 欠損検出、重複チェック、スパイク（急騰・急落）検出、日付整合性チェック
  - 各チェックは `QualityIssue` オブジェクトを返し、重大度に応じて呼び出し元が判断可能

- data/audit.py
  - 発注〜約定フローの監査ログ用スキーマ（signal_events, order_requests, executions）
  - 監査用テーブルの初期化関数（`init_audit_schema` / `init_audit_db`）
  - すべてのタイムスタンプは UTC 保存を前提

- config.py
  - 環境変数 / .env 管理（プロジェクトルートの `.env` / `.env.local` を自動読み込み）
  - 必須環境変数のラッパー（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

---

## 前提・依存

- Python 3.10+
  - 型ヒントに `X | Y` 表記を使用しているため Python 3.10 以上を想定しています
- 必須パッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API など）
- 環境変数またはプロジェクトルートの `.env` ファイルによる設定

インストール例（開発時）:
- 仮想環境作成後:
  - pip install -U pip
  - pip install duckdb
  - pip install -e .  （パッケージ化されていれば）

（このリポジトリ自体に setup.cfg/pyproject がある想定で上記コマンドを用いてください）

---

## 環境変数（.env）

このパッケージは、プロジェクトルート（.git または pyproject.toml がある階層）を基準に
`.env` と `.env.local` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば無効化可能）。

主な環境変数（README 用サンプル）:

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_station_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト値あり）
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
- SQLITE_PATH=data/monitoring.db    # デフォルト
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

`.env` のフォーマットは typical な shell-style（コメント対応、シングル/ダブルクォート対応）です。

---

## セットアップ手順（簡易）

1. Python 3.10+ の仮想環境を作成して有効化
2. 依存ライブラリをインストール
   - pip install duckdb
   - その他、プロジェクトで必要なパッケージを追加（logging 等は標準）
3. プロジェクトルートに `.env`（および `.env.local`）を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化
   - 初回は `init_schema()` を呼び出して DB ファイルとテーブルを作成します

---

## 使い方（サンプルコード）

以下は最小限の操作例です。実際はアプリケーション側でエラーハンドリング・ロギングを追加してください。

- DuckDB スキーマ初期化（初回のみ）

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 監査テーブルを既存コネクションに追加する

  ```python
  from kabusys.data.audit import init_audit_schema

  # conn は init_schema() 等で取得した DuckDB 接続
  init_audit_schema(conn)
  ```

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- J-Quants から直接データを取得・保存（テスト用途）

  ```python
  from kabusys.config import settings
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

- 品質チェックの単体実行

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- J-Quants の認証にはリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。`get_id_token()` がリフレッシュ処理を行います。
- `jquants_client` は API レート制限（120 req/min）を守るためのスロットリングと、レスポンスに対するリトライロジックを実装しています。

---

## 主要な API（モジュール毎）

- kabusys.config
  - settings: 環境変数ラッパー（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level）
  - 自動 .env ロードを行う（無効化可）

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブル作成）
  - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None) -> id token
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ実行

- kabusys.data.quality
  - run_all_checks(conn, ...) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(db_path)

---

## ディレクトリ構成

（プロジェクトの `src/kabusys` 以下にある主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

説明:
- data: データ取得、ETL、スキーマ、品質チェック、監査ログ等に関する実装を含みます。
- strategy / execution / monitoring: 戦略や発注、監視に関する名前空間（現状はパッケージ初期化のみで実装は別途）。

---

## 運用上の注意 / トラブルシューティング

- .env の自動読み込み
  - パッケージはプロジェクトルート（.git あるいは pyproject.toml の階層）を基準に `.env` と `.env.local` を自動読み込みします。
  - テストや明示的な環境管理のため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動読み込みを無効化できます。

- トークン・認証エラー
  - jquants_client のリクエストで 401 が返った場合はトークン自動更新を試みます（1 回だけリトライ）。トークンに不備がある場合は `JQUANTS_REFRESH_TOKEN` を見直してください。

- レート制限・リトライ
  - J-Quants API の仕様に合わせ、120 req/min のレート制限を守る実装が入っています。大量取得や並列取得時は制限に注意してください。

- DuckDB スキーマの冪等性
  - スキーマ初期化・保存処理は冪等（ON CONFLICT DO UPDATE）を考慮して実装されています。既存データを上書きする可能性があるため運用時はバックアップを推奨します。

---

## 開発・拡張のヒント

- strategy / execution 層は現状プレースホルダです。特徴量テーブル（features）や ai_scores テーブルに合わせて戦略モジュールを実装できます。
- ETL のジョブを定期実行する場合は、ジョブスケジューラ（cron, Airflow など）で `run_daily_etl()` を呼ぶか、専用の CLI を実装してください。
- 監査ログは削除しない前提の設計です。長期保存を考慮してファイル配置・アーカイブ運用を検討してください。

---

以上が本パッケージの README です。必要であれば、セットアップスクリプト（Makefile / CLI）や具体的な運用手順（Airflow / systemd など）に関するテンプレートも作成できます。どの部分をより詳しく書くか指示してください。