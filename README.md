# KabuSys

日本株向け自動売買基盤（KabuSys）  
バージョン: 0.1.0

軽量なデータレイヤ（DuckDB）と環境設定管理を備えた自動売買システムのコアライブラリです。戦略（strategy）、発注/実行（execution）、監視（monitoring）等のコンポーネントを収容するための骨組みと、DuckDB スキーマの初期化機能を提供します。

---

## 主な機能

- 環境変数 / .env ファイルの自動読み込み（プロジェクトルートを探索）
  - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - `.env` → `.env.local` の順で読み込み（OS 環境変数は保護）
- 設定ラッパー `kabusys.config.settings`
  - J-Quants、kabuステーション、Slack、DB パス、動作環境などをプロパティで取得
- DuckDB のスキーマ定義と初期化
  - Raw / Processed / Feature / Execution の層に分かれたテーブル定義
  - インデックス定義、外部キー依存を考慮したテーブル作成順を実装
  - `init_schema()`・`get_connection()` を公開 API として提供

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法 (X | Y) を使用）
- pip が利用可能

推奨手順（プロジェクトルートで実行）:

1. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必須パッケージのインストール
   ```
   pip install duckdb
   ```
   （このリポジトリがパッケージ化されている場合は `pip install -e .`）

3. 環境変数ファイルを作成
   - プロジェクトルートに `.env` を置くと、起動時に自動で読み込まれます。
   - サンプル（`.env.example` を参考に）:

   ```
   # .env (例)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL は未設定ならデフォルト: http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO            # DEBUG/INFO/WARNING/ERROR/CRITICAL
   ```

4. 自動 env ロードを無効にする（テストなどで）
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方

以下は基本的な利用例です。Python から直接利用できます。

- 設定の取得
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print("DuckDB path:", settings.duckdb_path)
  print("Environment:", settings.env)  # development / paper_trading / live
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # ファイル DB を使う場合
  conn = init_schema(settings.duckdb_path)

  # メモリ DB を使う場合
  conn_mem = init_schema(":memory:")
  ```

- 既存 DB への接続（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  ```

注意点:
- 必須環境変数（未設定時は ValueError を送出）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかである必要があります
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれか

---

## ディレクトリ構成

主要なファイル/モジュールは以下のとおりです（省略可能な空 __init__ 等を含む）:

- src/
  - kabusys/
    - __init__.py                # パッケージ定義（version 等）
    - config.py                  # 環境変数／設定管理（自動 .env 読み込み、Settings クラス）
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py               # 戦略ロジックを置く場所（将来実装）
    - execution/
      - __init__.py               # 発注・実行ロジック（将来実装）
    - monitoring/
      - __init__.py               # 監視・メトリクス収集（将来実装）

主要 API:
- from kabusys.config import settings
- from kabusys.data.schema import init_schema, get_connection

---

## 開発メモ・参考

- .env 自動読み込みは、現在のファイル（config.py）位置からプロジェクトルートを探索して行います。探索基準は .git または pyproject.toml の有無です。
- .env のパースはシェルライクな基本ルールに対応（export プレフィックス、クォート、インラインコメント処理など）。OS 環境変数は保護され、`.env.local` は `.env` の上書きとして扱われます。
- DuckDB スキーマは冪等（既存テーブルがあればスキップ）です。初回は必ず `init_schema()` を呼んでください。
- 将来的には strategy / execution / monitoring に具体的な実装を追加していきます。

---

必要であれば、README に例の .env.example を追加したり、CI / テスト実行方法、依存パッケージ一覧（requirements.txt）を追記します。追加したい情報があれば教えてください。