# KabuSys

日本株向けの自動売買（アルゴリズムトレーディング）用ライブラリの骨組みです。  
データ取得・格納（DuckDB）・特徴量テーブル・発注/約定管理までを想定したスキーマと、環境変数ベースの設定管理を含みます。

バージョン: 0.1.0

主なエクスポート:
- パッケージ名: kabusys
- モジュール: data, strategy, execution, monitoring

---

## プロジェクト概要

KabuSys は次の要素を提供します。

- 環境変数からの設定読み込み（.env 自動ロード機能）
- DuckDB を用いたデータベーススキーマ（Raw / Processed / Feature / Execution の多層構造）
- 各レイヤーに対応するテーブル定義とインデックス
- 初期化ユーティリティ（スキーマ作成、接続取得）
- 戦略／発注／監視モジュールのためのパッケージ構成（骨組み）

現在は主に設定管理と DuckDB スキーマ定義が実装されています。

---

## 機能一覧

- 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）
  - export 形式、クォート、インラインコメントを考慮したパース
  - 必須値を要求するヘルパ（Settings クラス経由）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
- DuckDB スキーマ（src/kabusys/data/schema.py）
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なインデックス定義、外部キー制約、データ型制約を含む DDL を提供
  - init_schema(db_path) でスキーマを冪等的に初期化
  - get_connection(db_path) で既存 DB へ接続

---

## 必要条件

- Python 3.10 以上（Union 型表記 Path | None 等を使用しているため）
- 依存ライブラリ:
  - duckdb

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb

パッケージ配布形式に合わせて:
- pip install -e . などでプロジェクトをインストールしてください（setup/pyproject の構成に依存）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール:
   - pip install duckdb
   - （将来的に Slack や kabu API 用のクライアントが必要なら別途インストール）
3. リポジトリルートに .env または .env.local を作成（下記例参照）
   - OS 環境変数が優先される点に注意
4. DB スキーマの初期化:
   - Python REPL、スクリプト、またはアプリ起動時に init_schema を呼ぶ

注意:
- 自動 .env 読み込みはデフォルトで有効。テストや CI で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 値が設定されていると自動.env読み込みをスキップ

サンプル .env:
KABUSYS の自動解析は export 形式やクォート等を許容します。

例 (.env):
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方

- 設定の取得:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path などのプロパティで取得できます。必須変数が欠けている場合は ValueError が発生します。

- DuckDB スキーマ初期化:
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - init_schema(settings.duckdb_path)

  サンプル:
  >>> from kabusys.config import settings
  >>> from kabusys.data.schema import init_schema, get_connection
  >>> conn = init_schema(settings.duckdb_path)  # ファイル作成 + テーブル作成
  >>> # または既存 DB に接続するだけなら:
  >>> conn2 = get_connection(settings.duckdb_path)

- 自動 .env 読み込みの仕組み:
  - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から .env と .env.local を探索して読み込みます
  - 読み込み順序: .env（override=False） → .env.local（override=True）
  - OS 環境変数は上書きされません（protected）

- .env のパース挙動:
  - 空行・# 始まりは無視
  - export KEY=val 形式に対応
  - シングル/ダブルクォート内はエスケープを考慮して読み取り
  - クォートなしの行では '#' の前にスペース/タブがある場合のみコメントとみなす

---

## API（主な関数 / クラス）

- Settings クラス（単一インスタンス settings）
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id
  - duckdb_path (Path), sqlite_path (Path)
  - env, log_level, is_live, is_paper, is_dev

- init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 指定パスの DuckDB を初期化して全テーブルとインデックスを作成（冪等）
  - db_path が ":memory:" ならインメモリ DB を使用
  - 親ディレクトリがなければ自動作成

- get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 既存の DuckDB に接続（スキーマ初期化は行わない）

---

## ディレクトリ構成

主要ファイルと概要:

- src/
  - kabusys/
    - __init__.py                # パッケージメタ情報（__version__, __all__）
    - config.py                  # 環境変数・設定管理（Settings, 自動 .env ロード）
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化ロジック（init_schema, get_connection）
    - strategy/
      - __init__.py              # 戦略ロジック用モジュール（拡張場所）
    - execution/
      - __init__.py              # 発注・約定ロジック用モジュール（拡張場所）
    - monitoring/
      - __init__.py              # 監視・メトリクス用モジュール（拡張場所）

README 以外に存在が想定されるファイル:
- .env.example（実運用時のテンプレートを置くことを推奨）
- pyproject.toml / setup.cfg など（配布・ビルド用）

---

## 開発メモ / 注意点

- Settings のプロパティは実行時に環境変数を読み出します。テスト時に環境を差し替える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、テストコード内で os.environ を操作してください。
- DuckDB スキーマは外部キーやチェック制約を多用しているため、データ投入時は制約を満たすように注意してください。
- 現在は戦略・発注・監視の具体的な実装は骨組みのみです。そこに具体的なアルゴリズムや API クライアントを実装していく想定です。

---

必要に応じて README に追記します（例: CI 手順、テストコマンド、依存ライブラリの詳細、.env.example の完全版など）。追加したい情報があれば指示してください。