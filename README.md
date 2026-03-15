# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）

このリポジトリは、J-Quants API や kabuステーション 等と連携してデータ取得・スキーマ管理・監査ログ・発注フローの基盤を提供する内部ライブラリ群です。DuckDB を使ったデータレイヤー設計（Raw / Processed / Feature / Execution）や監査テーブルを含みます。

バージョン: 0.1.0

---

## 概要

- J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー）
  - レート制限（120 req/min）を遵守する RateLimiter 実装
  - 指数バックオフによるリトライ（最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を抑止
  - DuckDB へ冪等的に保存（ON CONFLICT ... DO UPDATE）
- DuckDB 用スキーマ定義（raw / processed / feature / execution）
  - テーブル定義・インデックス・初期化関数を提供
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 までのトレーサビリティを保持する監査テーブル群
  - order_request_id を冪等キーとして二重発注を防止
- 環境変数設定管理（.env 自動ロード、必須チェック等）

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - API レート制御・リトライ・トークン自動更新・ページネーション対応
- data.schema
  - init_schema(db_path) : DuckDB スキーマを初期化して接続を返す
  - get_connection(db_path) : 既存 DB へ接続
- data.audit
  - init_audit_schema(conn) : 監査ログテーブルを既存接続に追加
  - init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す
- config
  - Settings クラス経由で環境変数を型安全に取得
  - 自動 .env 読み込み（プロジェクトルートにある .env / .env.local、.git または pyproject.toml を基準）
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

前提:
- Python 3.10+（typing の | None 等を使用）
- pip

1. リポジトリをチェックアウト／クローン

2. 開発環境にインストール（例）
   ```
   pip install -e .    # パッケージ化されていれば
   pip install duckdb
   ```
   ※ プロジェクトに pyproject.toml / requirements を用意している場合は、そちらに従ってください。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として保存すると自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite DB（省略時: data/monitoring.db）
   - KABUSYS_ENV : 実行環境（development / paper_trading / live、省略時: development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時: INFO）

5. サンプル .env（プロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

- スキーマ初期化（DuckDB）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルと親ディレクトリを自動作成
  ```

- J-Quants から日足を取得して保存する例
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

  # 全銘柄、期間指定など
  from datetime import date
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))

  saved = save_daily_quotes(conn, records)
  print(f"保存件数: {saved}")
  ```

- 監査ログの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema で取得した DuckDB 接続
  init_audit_schema(conn)
  ```

- 監査専用 DB を作る場合
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- トークン取得（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意事項:
- fetch_* 系はページネーションに対応しています。
- jquants_client は内部で 120 req/min のレート制御、リトライ、401 のトークン自動更新を行います。
- 保存関数は冪等（ON CONFLICT DO UPDATE）なので同じデータを何度保存しても上書きされます。
- すべてのタイムスタンプは UTC を使う設計（監査テーブルは init_audit_schema で SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

以下は主要なファイルとディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得・保存ロジック）
    - schema.py              : DuckDB スキーマ定義と初期化
    - audit.py               : 監査ログ（signal → order → execution のトレーサビリティ）
    - audit.py               : 監査テーブルの初期化および init_audit_db
  - strategy/
    - __init__.py            : 戦略関連モジュールのエントリ（空のパッケージ）
  - execution/
    - __init__.py            : 発注／約定関連モジュールのエントリ（空のパッケージ）
  - monitoring/
    - __init__.py            : モニタリング関連（空のパッケージ）

主なファイルの目的:
- config.py: .env の自動読み込みロジック（プロジェクトルート検出）、必須設定チェック、標準設定の提供
- data/schema.py: Raw / Processed / Feature / Execution レイヤーの DDL とインデックスを定義し init_schema() を提供
- data/jquants_client.py: API 呼び出し、レート制御、リトライ、トークン管理、DuckDB への安全な保存関数
- data/audit.py: 監査ログ用の DDL と初期化関数（init_audit_schema / init_audit_db）

---

## 運用上の注意（重要）

- KABUSYS_ENV の有効値: development, paper_trading, live
  - live に切り替えると実運用フラグとなるため慎重に設定してください。
- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml を基準に探索します。CI 等で動作させる際は CWD に依存しない点に注意してください。
- J-Quants API のレート制限（120 req/min）や証券会社 API の取り扱い（発注の冪等・再送）に注意して利用してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。運用時はバックアップや配置場所を検討してください。

---

必要があれば以下を追加で作成できます:
- examples/ に実行スクリプト（データ取得・特徴量作成・シグナル生成など）
- pyproject.toml / requirements.txt の整備
- strategy / execution のサンプル実装テンプレート

ご希望があれば README に具体的なコード例や CLI 実行手順、CI 設定例などを追加します。