# KabuSys

日本株自動売買システムの骨組み（ライブラリ）。  
このリポジトリは、環境変数/設定管理、DuckDB を用いたデータスキーマ定義、及び戦略・実行・監視モジュールの基本構成を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したライブラリです。主な目的は次のとおりです。

- 環境変数や .env ファイルからの設定取得（自動ロード機能付き）
- DuckDB を用いたデータベーススキーマの定義・初期化（Raw / Processed / Feature / Execution の多層構造）
- 戦略（strategy）、発注/実行（execution）、監視（monitoring）モジュールのためのパッケージ構成（骨組み）

現状は基盤実装（設定管理・スキーマ初期化）が中心で、戦略や実行ロジックは各自実装して拡張する想定です。

---

## 機能一覧

- 環境変数・.env ファイルの自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` の順で読み込み
  - OS 環境変数を保護しつつ `.env.local` で上書き可能
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
  - シングルクォート/ダブルクォート、エスケープ、コメント処理に対応したパーサ実装
- 設定オブジェクト（`kabusys.config.settings`）
  - 必須/省略時のデフォルト値やバリデーションを備えたプロパティ群を提供
- DuckDB スキーマ定義（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 各レイヤーのテーブル DDL を定義
  - インデックス定義、依存関係を考慮したテーブル作成順により初期化を実行する `init_schema()` を提供
  - `get_connection()` で既存 DB へ接続可能
- パッケージ構成
  - `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` のプレースホルダ（拡張ポイント）

---

## 必要条件

- Python 3.10+
- 必要なパッケージ（最低限）
  - duckdb

インストール例は次節を参照してください。

---

## セットアップ手順

1. Python 仮想環境の作成（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージのインストール
   最低限 duckdb をインストールしてください（プロジェクトに requirements.txt があればそちらを利用）。
   ```bash
   pip install --upgrade pip
   pip install duckdb
   ```

3. 本パッケージを開発モードでインストール（任意）
   リポジトリ直下に `pyproject.toml` / `setup.py` がある想定で：
   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   必要な環境変数（少なくとも以下を設定してください）:

   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN（必須）
   - SLACK_CHANNEL_ID（必須）
   - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（任意、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（任意、"development" | "paper_trading" | "live"、デフォルト: development）
   - LOG_LEVEL（任意、"DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"、デフォルト: INFO）

   簡単にはプロジェクトルートに `.env` / `.env.local` を作成して設定してください。自動ロードはデフォルトで有効です。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

- 設定の参照
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print(settings.env, settings.is_dev)
  ```

- DuckDB スキーマの初期化（推奨: アプリ起動時に一度実行）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は Path オブジェクトを返します
  conn = init_schema(settings.duckdb_path)
  # conn は duckdb の接続オブジェクト（DuckDBPyConnection）
  ```

- 既存 DB へ接続（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  ```

- 例: テーブル一覧の確認
  ```python
  with conn:
      print(conn.execute("SHOW TABLES").fetchall())
  ```

---

## 設定の自動ロード挙動（補足）

- プロジェクトルート判定はこのパッケージのソース配置を基準に行われます（CWD には依存しません）。
- 読み込み順: OS 環境変数 > .env.local > .env
  - `.env` は既存の OS 環境変数を上書きしません（override=False）
  - `.env.local` は上書き可能（override=True）だが OS 環境変数は保護されます
- .env のパースは次の形式に対応:
  - export KEY=val
  - KEY="quoted value" / 'quoted value'（エスケープ対応）
  - コメント（#）の扱いはクォート外やスペース直前で処理

---

## ディレクトリ構成

（リポジトリの src 配下を想定）

- src/
  - kabusys/
    - __init__.py
      - パッケージエントリ（__version__ 等）
    - config.py
      - 環境変数/設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - schema.py
        - DuckDB スキーマ定義、初期化関数（init_schema, get_connection）
    - strategy/
      - __init__.py
      - （戦略ロジックを実装する場所）
    - execution/
      - __init__.py
      - （注文送信・実行管理を実装する場所）
    - monitoring/
      - __init__.py
      - （監視・アラート機能を実装する場所）

主要ファイルの説明:

- src/kabusys/config.py
  - .env 自動ロード、設定値取得用プロパティ群、バリデーション、環境切替フラグ（is_live 等）
- src/kabusys/data/schema.py
  - DuckDB の DDL（raw_prices, prices_daily, features, signals, orders, trades, positions など多数）を定義
  - init_schema(db_path) で DB とスキーマを作成
- strategy / execution / monitoring
  - 将来的な機能拡張用のプレースホルダパッケージ

---

## 開発・拡張のポイント

- 戦略や発注ロジックは `kabusys.strategy` / `kabusys.execution` に実装してください。
- DuckDB のスキーマは既存の DDL に従っているため、既存レイヤー（Raw → Processed → Feature → Execution）にデータを流し込む形でパイプラインを構築できます。
- 外部 API キーやシークレットは必ず環境変数で管理してください（.env の場合でも公開リポジトリに含めないこと）。

---

必要に応じて、README に含めるサンプルワークフロー（データ取り込み→特徴量計算→シグナル生成→発注→監視）や .env.example のテンプレートを追加することもできます。追加希望があればお知らせください。