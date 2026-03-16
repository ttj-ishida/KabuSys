# KabuSys

日本株の自動売買プラットフォーム用ライブラリ（軽量コア）。データ取得、スキーマ管理、データ品質チェック、監査ログなど、戦略・実行パイプラインの基盤となる機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの内部ライブラリ群です。主に以下を目的としています。

- J-Quants API からの市場データ取得（OHLCV・財務・マーケットカレンダー）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution）管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注→約定までを追跡できる監査（Audit）テーブル
- 簡易な設定管理（.env / 環境変数）

設計上のポイント：
- API レート制限遵守（J-Quants: 120 req/min）とリトライ、トークンの自動更新
- データ取得時の fetched_at による時点のトレーサビリティ（look-ahead バイアス対策）
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE）で実装

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須設定の検査（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_* 関数で DuckDB に冪等保存（raw_prices / raw_financials / market_calendar）

- スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で DuckDB に全テーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) / init_audit_db(path)
  - signal_events / order_requests / executions を含む監査テーブル群

- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue リストを返す

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈の union 演算子 `|` を利用しているため）
- DuckDB を利用（Python パッケージ duckdb）

1. リポジトリをクローンし、パッケージをインストール（開発環境）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

   もしくは最低限の依存だけ入れる場合:
   ```
   pip install duckdb
   ```

2. 環境変数を用意
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および必要なら `.env.local`）を配置します。自動読み込みはデフォルトで有効です。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意/デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   自動 env ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 基本的な使い方（例）

以下はライブラリの代表的な利用例です。各コードは Python スクリプトや REPL から実行できます。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # :memory: も可
  ```

- J-Quants から日足を取得して保存
  ```python
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=date(2022,1,1), date_to=date(2022,12,31))
  inserted = save_daily_quotes(conn, records)
  print(f"保存件数: {inserted}")
  ```

- 財務データやマーケットカレンダーの取得・保存も同様に fetch_* / save_* を使用します。

- 監査スキーマの初期化（既存の conn に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

- id_token 取得（必要に応じて明示的に）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

注意点:
- J-Quants API 呼び出しは内部でレートリミッタ・リトライ・401→トークン自動更新を行います。
- save_* 系は fetched_at を付与し、主キーが一致する場合は更新します（冪等）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み・Settings クラスを提供
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* / get_id_token
  - schema.py
    - DuckDB の DDL 定義と init_schema / get_connection
  - audit.py
    - 監査ログ用テーブル定義と初期化
  - quality.py
    - データ品質チェック機能（QualityIssue データクラスと各チェック）
  - (その他: raw/news/execution スキーマ等を含む DDL)
- strategy/
  - __init__.py  （戦略モジュール用のプレースフォルダ）
- execution/
  - __init__.py  （発注/執行モジュール用のプレースフォルダ）
- monitoring/
  - __init__.py  （監視用のプレースフォルダ）

プロジェクトルートには通常以下が存在（このリポジトリのルート判定に使用）
- .git
- pyproject.toml（存在する場合）

---

## 注意事項 / 補足

- Python バージョン: 本コードは Python 3.10 以降を想定しています（型アノテーションに `X | Y` を使用）。
- ネットワーク/API 利用: J-Quants の利用には有効なリフレッシュトークンが必要です。レート制限や API 利用規約に従ってください。
- DuckDB: ファイルパスの親ディレクトリが存在しない場合は自動作成されます。
- ログ/監視: Settings.log_level に基づいてログレベルが決まります。運用時は KABUSYS_ENV を適切に設定してください（paper_trading/live）。
- セキュリティ: .env に機密情報を置く場合は取り扱いに注意してください。`.env.local` はローカル上書き用に使えます。

---

必要であれば、README に開発者向けの CONTRIBUTING、API 仕様の詳細、.env.example のサンプルやユニットテスト実行手順なども追記できます。どの情報を優先して追加しますか？