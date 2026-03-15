# KabuSys

日本株向けの自動売買基盤ライブラリ（骨組み）。データ収集・スキーマ管理・戦略・発注・モニタリングを想定したパッケージ構成を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。本リポジトリは以下を提供します。

- 環境変数管理（.env 自動ロード、必須設定の検証）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）
- 戦略、実行、モニタリング用の名前空間（拡張ポイント）

この README は現状のコードベースに基づいた使い方・セットアップ手順を説明します。

---

## 主な機能一覧

- 環境変数読み込み・管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（OS環境変数が優先）
  - export 形式、クォート・エスケープ、インラインコメント等を考慮したパーサ
  - 必須変数未設定時に明示的にエラーを発生
- DuckDB スキーマ定義・初期化
  - raw / processed / feature / execution 層のテーブル定義
  - インデックスおよび外部キー制約を考慮した DDL を準備
  - init_schema(db_path) による冪等的な初期化
- 拡張ポイント
  - `kabusys.strategy`、`kabusys.execution`、`kabusys.monitoring` などモジュールを追加して機能拡張可能

---

## 要件

- Python 3.10 以上（型注釈に `X | Y` 構文を使用）
- 依存パッケージ:
  - duckdb

必要に応じて仮想環境を使用してください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

   git clone ...（省略）

2. 仮想環境の作成（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール

   pip install duckdb

   （将来的に requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. パッケージをソース開発モードでインストール（任意）

   pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（例）

以下の環境変数がコード内で参照されます。必須のものは未設定時に ValueError を投げます。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

サンプル `.env`:

    # .env (例)
    JQUANTS_REFRESH_TOKEN="your_jquants_token"
    KABU_API_PASSWORD="your_kabu_password"
    SLACK_BOT_TOKEN="xoxb-..."
    SLACK_CHANNEL_ID="C12345678"
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb

注意:
- OS 環境変数が最優先で、次に `.env.local`、次に `.env` の順で読み込まれます（ただし `.env.local` は既に存在する OS 環境変数を上書きしません）。
- `.env` のパースは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応しています。

---

## 使い方（簡単な例）

- 設定値の取得:

    from kabusys.config import settings

    # 必須変数は未設定だと ValueError
    token = settings.jquants_refresh_token
    api_url = settings.kabu_api_base_url
    is_live = settings.is_live

- DuckDB スキーマ初期化:

    from kabusys.data.schema import init_schema, get_connection
    from kabusys.config import settings

    # settings.duckdb_path は Path を返す
    conn = init_schema(settings.duckdb_path)
    # またはインメモリ DB
    # conn = init_schema(":memory:")

    # 既存 DB へ接続（スキーマの初期化は行わない）
    conn2 = get_connection(settings.duckdb_path)

- エラー例（環境変数未設定）:
  - settings.jquants_refresh_token を参照した際に設定がないと ValueError が発生します。テスト時は明示的に環境変数をセットするか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを止め、手動で環境を設定してください。

---

## ディレクトリ構成

以下はリポジトリの主要ファイル / ディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py               (パッケージ定義、__version__ = "0.1.0")
    - config.py                 (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py               (DuckDB スキーマ定義・初期化: init_schema, get_connection)
    - strategy/
      - __init__.py             (戦略関連の拡張ポイント)
    - execution/
      - __init__.py             (発注実行関連の拡張ポイント)
    - monitoring/
      - __init__.py             (モニタリング関連の拡張ポイント)

その他:
- pyproject.toml (存在する場合プロジェクトルート検出に使用)
- .git/ (存在する場合プロジェクトルート検出に使用)
- .env, .env.local (プロジェクトルートに置くことで自動ロードされる)

---

## 開発メモ / 実装のポイント

- プロジェクトルート検出:
  - config._find_project_root() は __file__（このモジュールファイル）の親階層を遡って `.git` または `pyproject.toml` を探します。CWD 依存ではないため、パッケージ配布後も正しく動作します。検出できない場合は自動で .env を読み込みません。
- .env 読み込み優先順位:
  - OS 環境変数 > .env.local > .env
  - `.env.local` の読み込みは上書き（override=True）ですが、OS の既存キーは保護されています。
- DuckDB スキーマ:
  - init_schema は冪等で、既にテーブルが存在する場合はスキップします。
  - デフォルトの DB パスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）で、親ディレクトリがなければ自動で作成します。

---

必要に応じて README を拡張します（例: 実際の戦略実装例、発注フロー、モニタリングダッシュボードの統合方法、CI/CD、テスト手順など）。追加で盛り込みたい内容があれば指定してください。