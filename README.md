# KabuSys

KabuSys は日本株の自動売買システム（骨格）を提供する Python パッケージです。データ層（DuckDB スキーマ）、環境設定管理、戦略・実行・監視用のパッケージ構成を含み、実運用・ペーパートレード・開発環境に対応できるよう設計されています。

バージョン: 0.1.0

## 概要
- DuckDB を用いた永続化（Raw / Processed / Feature / Execution の多層スキーマ）
- .env / 環境変数による設定管理（自動読み込み機能あり）
- J-Quants、kabuステーション、Slack などの外部 API 設定に対応
- 戦略（strategy）、発注（execution）、監視（monitoring）用のモジュールを想定したパッケージ構成

## 主な機能一覧
- 環境変数/`.env` 読み込み（プロジェクトルート自動検出）
- 設定ラッパー `kabusys.config.settings`（必須チェック・デフォルト値）
- DuckDB スキーマ初期化関数 `kabusys.data.schema.init_schema()`（全テーブル・インデックスを作成）
- DuckDB 接続取得 `kabusys.data.schema.get_connection()`
- 戦略 / 発注 / 監視のためのパッケージ骨組み（`kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`）

## 要件
- Python 3.9+
- duckdb Python パッケージ

（プロジェクト依存パッケージは pyproject.toml / requirements を用意している想定です。開発環境では追加のパッケージが必要になる可能性があります。）

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します（省略可能）。
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化します（推奨）。
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストールします（例: duckdb）。
   pip install duckdb

   開発インストール（プロジェクトルートに pyproject.toml がある場合）:
   pip install -e .

4. 環境変数を設定します（後述の .env 参照）。プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（無効化も可能）。

## 環境変数（主要なもの）
以下はこのパッケージで参照される主要な環境変数一覧です。必須のものは明記しています。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - デフォルト: `http://localhost:18080/kabusapi`
- SLACK_BOT_TOKEN (必須)
  - Slack ボット用トークン
- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV (任意)
  - 環境。`development`（デフォルト）/ `paper_trading` / `live`
- LOG_LEVEL (任意)
  - ログレベル。`INFO`（デフォルト）等。許容値: `DEBUG, INFO, WARNING, ERROR, CRITICAL`

Settings クラス経由で取得できます（例: `from kabusys.config import settings`）。

### .env 自動読み込みの挙動
- 自動読み込みはプロジェクトルート（`.git` または `pyproject.toml` が存在するディレクトリ）を基に行います。
- 読み込み順序と優先度:
  - OS 環境変数（最優先）
  - .env.local（上書き許可）
  - .env（上書き不可、未定義キーのみセット）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

### .env のパース挙動（主なルール）
- コメント行（# で始まる行）は無視
- `export KEY=val` 形式に対応
- 値はシングル/ダブルクォートで囲める。クォート内ではバックスラッシュによるエスケープを解釈
- クォート無しの値では、`#` の直前が空白またはタブであれば以降をコメントと扱う

## 使い方（簡単な例）

- 設定の参照:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print("env:", settings.env)
  print("is_live:", settings.is_live)
  ```

- DuckDB スキーマの初期化:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection

  # settings.duckdb_path は Path オブジェクト
  conn = init_schema(settings.duckdb_path)  # テーブルとインデックスを作成して接続を返す

  # 既存 DB に接続するだけの場合
  conn2 = get_connection(settings.duckdb_path)
  ```

- 自動 .env 読み込みを無効にしたい場合:
  - プロセス起動時に環境変数を設定:
    - Linux/macOS: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - Windows (PowerShell): $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"

  その後で `kabusys` を import してください。

## DuckDB スキーマについて
- テーブル設計は Raw / Processed / Feature / Execution の多層構造になっています。
- 代表的なテーブル:
  - raw_prices / raw_financials / raw_news / raw_executions
  - prices_daily / market_calendar / fundamentals / news_articles / news_symbols
  - features / ai_scores
  - signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
- インデックスは、銘柄×日付スキャンやステータス検索等を想定して作成されています。
- 初期化は `kabusys.data.schema.init_schema(db_path)` を呼びます（冪等）。

## ディレクトリ構成（主要ファイル）
プロジェクト内のおおまかな構成は以下のとおりです。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
    - strategy/
      - __init__.py            # 戦略関連（骨組み）
    - execution/
      - __init__.py            # 発注関連（骨組み）
    - monitoring/
      - __init__.py            # 監視関連（骨組み）

（実際のプロジェクトではさらにサブモジュールやユーティリティが追加されます。）

## 開発
- パッケージとして開発中は `pip install -e .` で編集可能インストールを行ってください。
- テストを追加する場合は、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みの影響を排除することが便利です。

## 注意事項
- 設定取得時に必須環境変数が未設定の場合、`ValueError` が送出されます（例: `JQUANTS_REFRESH_TOKEN`）。
- DuckDB のファイルパスの親ディレクトリが存在しない場合は `init_schema()` が自動で作成します。
- `get_connection()` はスキーマ初期化を行いません。初回は `init_schema()` を使用してください。

---

この README は現在のコードベース（設定管理と DuckDB スキーマ初期化を中心にした骨組み）に基づく基本的な利用方法をまとめたものです。戦略実装や発注フロー、監視機能の実装はプロジェクトの要件に応じて追加してください。