KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームの骨組みを提供する Python パッケージです。  
データ層・特徴量層・発注/約定の実行層、および監査用テーブルを用意し、戦略ロジックとブローカー接続を結び付けるための基盤を備えています。

主な目的：
- 株価・財務・ニュース等のデータを保存・加工するスキーマ
- 戦略で利用する特徴量テーブル
- シグナル・発注・約定・ポジション管理テーブル
- 発注フローの完全なトレーサビリティを確保する監査ログ

機能一覧
--------
- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートが .git または pyproject.toml により判定）
  - 必須変数未設定時に明確なエラーを投げる Settings API
  - ランタイム環境（development / paper_trading / live）とログレベルの検証

- DuckDB ベースのデータスキーマ（冪等にテーブル作成）
  - Raw / Processed / Feature / Execution の多層スキーマ
  - 頻出クエリのためのインデックス定義
  - init_schema() / get_connection() による初期化・接続

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによりシグナル→発注→約定の連鎖を UUID で追跡
  - 冪等キー（order_request_id / broker_execution_id）を考慮した設計
  - init_audit_schema() / init_audit_db() による初期化
  - 監査タイムスタンプは UTC に固定（初期化時に TimeZone='UTC' を設定）

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントの union 演算子（|）などを使用）
- pip（Python のパッケージ管理）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 最低限：duckdb
     - pip install duckdb
   - 実運用では Slack や kabu API クライアント等が別途必要になるため適宜追加してください。

3. ソースをプロジェクトに配置
   - リポジトリをクローンするか、パッケージを適切な位置に置いて Python のパスに含める。
   - （開発時）プロジェクトルートに .git または pyproject.toml が存在することを確認してください（.env 自動読み込みのため）。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に .env または .env.local を配置すると自動で読み込まれます。
   - 自動ロードを無効にしたい場合：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

.sample .env（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方
------

設定（Settings）
- 設定は kabusys.config.settings から利用できます。必須変数が欠けていると ValueError が発生します。

例：
- from kabusys.config import settings
- token = settings.jquants_refresh_token
- if settings.is_live: ...

データベーススキーマの初期化（DuckDB）
- 永続 DB を初期化する例：
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - この呼び出しは必要な親ディレクトリを自動作成し、すべてのテーブルとインデックスを作成します（冪等）。

- インメモリ DB（テスト用）の初期化例：
  - conn = init_schema(":memory:")

- 既存 DB への接続（スキーマ初期化はしない）：
  - from kabusys.data.schema import get_connection
  - conn = get_connection("data/kabusys.duckdb")

監査ログの初期化
- 既存の DuckDB 接続に監査テーブルを追加する：
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)
  - この関数は接続に対して UTC タイムゾーン設定（SET TimeZone='UTC'）を行います。

- 監査専用 DB を新規に作る場合：
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

シンプルな起動スクリプト例
- db を初期化して接続を得る最小例：
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

注意点
- Settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）は未設定時に ValueError を投げます。デプロイ前に .env を用意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、ルートが検出されない環境では自動ロードされません。
- 監査ログはすべて UTC タイムスタンプで保存されます（init_audit_schema が SET TimeZone='UTC' を実行）。

主な API（抜粋）
- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> duckdb connection

ディレクトリ構成
----------------
以下は本パッケージに含まれる主要ファイルの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py                # パッケージのメタ情報（__version__ 等）
    - config.py                  # 環境変数 / Settings 管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化（データ層）
      - audit.py                 # 監査ログ（トレーサビリティ）用スキーマ
      - audit.py
      - audit.py
    - strategy/
      - __init__.py              # 戦略関連モジュールのエントリポイント（拡張ポイント）
    - execution/
      - __init__.py              # 発注・実行関連モジュールのエントリポイント（拡張ポイント）
    - monitoring/
      - __init__.py              # 監視・メトリクス関連（拡張ポイント）

（注）上記は現状の主要ファイルのみを列挙しています。実プロジェクトでは strategy, execution, monitoring 以下に戦略ロジックやブローカー連携、監視用コードを追加していきます。

拡張と運用のヒント
------------------
- strategy / execution / monitoring モジュールは現状エントリポイントのみ用意されているため、ここに戦略ロジック、リスク管理、kabu API クライアント、Slack 通知等を実装していきます。
- 発注処理では audit テーブル群（order_requests / executions）を用いて冪等性とトレーサビリティを確保する設計にしています。運用時は order_request_id の生成と再送時の扱いを厳密に実装してください。
- DuckDB ファイルは軽量でローカル分析に適しています。大量データや同時アクセスが多い場合は運用上の検討（分割、バックアップ、移行）を行ってください。

サポート / 参考
----------------
- DuckDB: https://duckdb.org/
- 環境変数定義は .env.example を用意してチームで共有することを推奨します。

以上がこのリポジトリの概要と利用方法です。開発を進める際は strategy / execution 層へ具体的実装を追加し、監査ログとデータ層を用いた完全な自動売買フローの実現を目指してください。