# KabuSys

日本株向けの自動売買基盤ライブラリ（プロジェクト初期版）

バージョン: 0.1.0

概要:
- 市場データの取り込み・スキーマ管理、特徴量レイヤ、発注・実行レイヤを備えた日本株自動売買システムの基盤モジュール群。
- DuckDB を用いた永続化スキーマを定義・初期化する機能、環境変数による設定管理（.env 自動読み込み）などを提供します。
- 戦略（strategy）、実行（execution）、監視（monitoring）などのサブパッケージの雛形を含みます。

主な機能
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（CWD に依存しない探索）
  - OS 環境変数と .env の優先順位制御（OS > .env.local > .env）
  - 必須設定を取得する Settings クラス（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）
  - 自動読み込みを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを DDL として定義
  - テーブル作成（冪等）・インデックス作成処理を行う init_schema(db_path)
  - 既存 DB に接続する get_connection(db_path)
  - :memory: を指定してインメモリ DB の使用が可能
- パッケージ構成の雛形
  - strategy / execution / monitoring のサブモジュール（将来の拡張箇所）

セットアップ手順（開発環境）
1. Python バージョン
   - Python 3.10 以上推奨（Union 型に | を使用しているため）
2. リポジトリをクローン
   - git clone <リポジトリ>
3. 依存パッケージをインストール
   - 例（pip を使用した開発インストール）:
     ```
     pip install -e .
     pip install duckdb
     ```
     （プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください）
4. 環境変数ファイルを用意
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を自動検出して .env/.env.local を読み込みます。
   - 自動読み込みを一時的に無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. .env の例（.env.example を参考に作成してください）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（省略時はデフォルト）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行モード
   KABUSYS_ENV=development  # development | paper_trading | live

   # ログレベル
   LOG_LEVEL=INFO
   ```

使い方（簡単なサンプル）
- 環境設定の利用
  ```python
  from kabusys.config import settings

  # 必須項目は設定されていないと ValueError が発生します
  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  print(settings.env, settings.log_level)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  # settings.duckdb_path は Path を返す
  conn = init_schema(settings.duckdb_path)  # ファイルがなければ parent を自動作成
  # 以降 conn.execute(...) で SQL 実行可能
  ```

- インメモリ DB の初期化（テスト等）
  ```python
  conn = init_schema(":memory:")
  ```

- 自動 .env 読み込みの挙動
  - 読込優先順位: OS 環境変数 > .env.local > .env
  - .env/.env.local のパースはシェル風：`export KEY=val`、クォート、行末コメント等に対応します。

API（主要エンドポイント）
- kabusys.config
  - settings: Settings インスタンス（プロパティ一覧）
    - jquants_refresh_token
    - kabu_api_password
    - kabu_api_base_url
    - slack_bot_token
    - slack_channel_id
    - duckdb_path（Path）
    - sqlite_path（Path）
    - env, log_level, is_live, is_paper, is_dev
- kabusys.data.schema
  - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py                -- パッケージメタ情報（version=0.1.0）
  - config.py                  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                -- DuckDB スキーマ定義と初期化
  - strategy/
    - __init__.py              -- 戦略モジュール群（雛形）
  - execution/
    - __init__.py              -- 発注・実行モジュール群（雛形）
  - monitoring/
    - __init__.py              -- 監視・記録モジュール（雛形）

データベース（スキーマ）について
- 層構造:
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 各テーブルはCREATE TABLE IF NOT EXISTS による冪等的な作成。よく使うクエリ向けのインデックスも作成されます。
- 外部キー制約は一部に設定されています（例: news_symbols.news_id -> news_articles.id, orders.signal_id -> signal_queue.signal_id, trades.order_id -> orders.order_id）。

注意事項 / 補足
- Settings は環境変数の値を直接参照します。必須の環境変数が未設定だと ValueError が送出されます。
- .env パースは一般的な shell 形式に合わせていますが、特殊ケースでは期待どおりに処理されない可能性があります。必要に応じて .env.local を使用してください。
- DuckDB の Python バインディング（duckdb）が必要です。実行環境にインストールしてください。
- 本リポジトリは基盤ライブラリの初期段階です。戦略ロジック・実際の発注統合（kabuステーション API 呼び出し等）は別モジュールで実装してください。

ライセンス、貢献方法など
- （この README には含まれていませんが、実プロジェクトでは LICENSE ファイル、CONTRIBUTING ガイド、.env.example を用意することを推奨します。）

以上。必要であれば README に含める .env.example や、より詳細な API リファレンス、サンプル Jupyter ノートブック、スキーマ図（DataSchema.md 相当）を追記します。どれを追加したいか教えてください。