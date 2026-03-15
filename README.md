# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ管理、特徴量生成、取引実行・監視のための基盤的コンポーネント群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けの共通基盤ライブラリです。市場データや決算データ、ニュース、発注／約定情報を DuckDB に格納するためのスキーマ定義、環境変数による設定管理、取引実行や戦略を実装するためのモジュール構成を含みます。

主な目的は以下のとおりです。
- データレイヤ（Raw / Processed / Feature / Execution）を考慮した DuckDB スキーマ提供
- 環境変数を使った一元的な設定管理（自動 .env 読み込み機能付き）
- 各モジュール（data / strategy / execution / monitoring）の土台提供

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）からの自動読み込み（プロジェクトルートを基準）
  - 必須キーの取得 API（不足時は例外）
  - 実行環境（development / paper_trading / live）・ログレベル検証

- データベーススキーマ（DuckDB）
  - Raw 層: raw_prices / raw_financials / raw_news / raw_executions
  - Processed 層: prices_daily / market_calendar / fundamentals / news_articles / news_symbols
  - Feature 層: features / ai_scores
  - Execution 層: signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
  - 頻出クエリ向けのインデックスも作成

- DB 初期化ユーティリティ
  - init_schema(db_path) でテーブル／インデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続

- パッケージ化されたモジュール構成
  - kabusys.config（環境設定）
  - kabusys.data（スキーマ・データ操作）
  - kabusys.strategy（戦略用モジュール配置用）
  - kabusys.execution（発注周り）
  - kabusys.monitoring（監視・ログ／メトリクス）

---

## 前提条件（動作環境）

- Python 3.10+
- duckdb（Python バインディング）
- その他、戦略や実行部で必要な外部 API クライアント等（J-Quants / kabuステーション / Slack など）は各自設置

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - 最低限、duckdb が必要です。
   ```
   pip install duckdb
   ```
   - 開発時は `pip install -e .`（パッケージとしてインストール可能な setup / pyproject がある場合）

4. 環境変数ファイル（.env）の準備
   プロジェクトルートに `.env` および必要に応じて `.env.local` を作成してください（サンプルは下記参照）。

5. データベース初期化（例）
   Python REPL やスクリプト内で以下を実行して DuckDB スキーマを作成します（初回のみ）。
   ```py
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   db_path = settings.duckdb_path  # デフォルトは data/kabusys.duckdb
   conn = init_schema(db_path)
   # conn を使って追加の初期化や確認が可能
   ```

---

## 環境変数（.env）例

プロジェクトルートに `.env`（と必要なら `.env.local`）を置くことで自動読み込みされます。OS 環境変数が優先され、`.env.local` は `.env` を上書きする挙動です。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル (.env.example):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# Optional: API のベース URL（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# System
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- 必須キーに未設定でアクセスすると例外（ValueError）が送出されます（例: settings.jquants_refresh_token）。
- .env のパースはシェル風のクォートやコメントをある程度サポートしています。

---

## 使い方（基本例）

- 設定の取得
```py
from kabusys.config import settings

print(settings.env)           # development / paper_trading / live
print(settings.log_level)     # DEBUG / INFO / ...
print(settings.duckdb_path)   # Path オブジェクトで返る
```

- DB スキーマの初期化（新規 DB）
```py
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルを自動で作成してスキーマをセットアップ
# conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- 既存 DB へ接続（スキーマ初期化は行わない）
```py
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みの制御
  - デフォルトでは、パッケージロード時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます。
  - テストなどで自動読み込みを無効化したい場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- パッケージ情報
```py
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

※ strategy / execution / monitoring モジュールは骨格を提供しています。具体的な戦略や API 呼び出し（kabuステーションへの発注や J-Quants からのデータ取得、Slack 通知等）は個別に実装してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py            — パッケージ初期化（__version__ 等）
  - config.py              — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py            — DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - strategy/
    - __init__.py          — 戦略モジュール置き場（拡張用）
  - execution/
    - __init__.py          — 発注・約定処理置き場（拡張用）
  - monitoring/
    - __init__.py          — 監視用モジュール置き場（拡張用）

- .env, .env.local         — （プロジェクトルートに置く）環境設定ファイル（自動読み込み対象）
- data/                    — デフォルトの DB/データ置き場（DUCKDB_PATH 等で変更可能）

---

## 開発・拡張のヒント

- DuckDB のスキーマは冪等に作成されます。フィールド追加や制約変更時はマイグレーション手順を検討してください。
- 実運用（live）では KABUSYS_ENV を `live` に設定し、発注前に充分な検証を行ってください。
- 外部 API の認証情報（Slack トークンや J-Quants トークン、kabu API パスワード等）は必ず安全に管理し、`.env` をバージョン管理に含めないでください（`.gitignore` へ追加）。

---

もし README に追加したい具体的な使用例（例: J-Quants からのデータ取り込み／サンプル戦略／Signal→Order フロー等）があれば、コードや要件を教えてください。サンプルと手順を追記します。