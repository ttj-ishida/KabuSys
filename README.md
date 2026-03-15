# KabuSys

日本株向けの自動売買システムの基盤ライブラリです。市場データの保存・スキーマ管理、環境設定の読み込み、戦略・発注・モニタリングのためのモジュール分割を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システム構築のための共通基盤を提供します。本リポジトリは以下の機能を中心に実装しています。

- 環境変数／.env ファイルからの設定読み込みとバリデーション
- DuckDB を用いたデータベーススキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- モジュール分割（data, strategy, execution, monitoring）による拡張性

このパッケージ自体は「基盤」部分であり、実際の取得ロジック、戦略、発注ロジックは各サブモジュールで実装していく想定です。

---

## 主な機能一覧

- settings（kabusys.config.Settings）
  - .env / .env.local / OS 環境変数から設定を読み込む（自動ロード）
  - 必須キーの存在チェック（未設定時は ValueError）
  - J-Quants, kabu API, Slack、DB パス、実行環境（development / paper_trading / live）などをプロパティとして提供

- 環境変数自動ロード
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions）
  - Processed Layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
  - Feature Layer（features, ai_scores）
  - Execution Layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - インデックス作成、テーブルの冪等生成
  - API: init_schema(db_path) / get_connection(db_path)

---

## 動作要件

- Python 3.10 以上（型アノテーションで `X | Y` を使用）
- duckdb Python パッケージ

必要に応じて、kabu API、J-Quants、Slack 用のクライアントライブラリ等を追加してください（このリポジトリにはそれらのクライアント実装は含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン／ダウンロード

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb
   - （開発時）ローカルパッケージインストール:
     - pip install -e .
     - ※ pyproject.toml / setup.py がある場合は通常のインストール方法に従ってください

4. 環境変数の設定
   - プロジェクトルートに `.env` として必要な環境変数を用意します。`.env.local` はローカル上書き用に使用できます。
   - 自動ロードはデフォルトで有効（OS 環境変数 > .env.local > .env）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（コードから参照される主なキー）
   - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - KABU_API_BASE_URL     : （任意、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack ボットトークン
   - SLACK_CHANNEL_ID      : 通知先の Slack チャンネル ID
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : モニタリング用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : 実行環境（development / paper_trading / live）（デフォルト development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（デフォルト INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

- 設定値の参照

```python
from kabusys.config import settings

# 必須値を取得（未設定時は ValueError）
token = settings.jquants_refresh_token
print("環境:", settings.env)
print("DuckDB path:", settings.duckdb_path)
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path を使用してスキーマ初期化
conn = init_schema(settings.duckdb_path)
# またはメモリ DB:
# conn = init_schema(":memory:")
```

- 既存 DB への接続（スキーマ初期化は行わない）

```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動環境読み込みを無効化したい場合（テスト等）

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# Windows (PowerShell)
# $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

---

## ディレクトリ構成

以下は主要なファイル／ディレクトリ構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py                      - パッケージ定義（__version__ 等）
    - config.py                        - 環境変数読み込み・Settings 定義
    - data/
      - __init__.py
      - schema.py                      - DuckDB スキーマ定義と初期化 API（init_schema / get_connection）
    - strategy/
      - __init__.py                     - 戦略モジュール（拡張用）
    - execution/
      - __init__.py                     - 発注・実行ロジック（拡張用）
    - monitoring/
      - __init__.py                     - 監視・モニタリング（拡張用）

README に記載のない追加の実装（戦略・API クライアント・通知など）は各サブモジュール配下に実装してください。

---

## 備考 / 実装上の注意

- .env のパーシングはシェル風の形式に近いですが完全互換ではありません（引用符やコメントの取り扱いに仕様あり）。詳細は kabusys.config._parse_env_line を参照してください。
- init_schema は冪等（既にテーブルが存在する場合はスキップ）で、安全に何度でも呼び出せます。
- DuckDB のファイルパスの親ディレクトリが存在しない場合、init_schema が自動で親ディレクトリを作成します。
- KABUSYS_ENV の値は厳格に検証されます（development / paper_trading / live のいずれか）。

---

必要であれば、.env.example の雛形や開発用の Dockerfile / docker-compose、CI 設定例、サンプル戦略の追加などの README を拡張できます。どの情報が欲しいか教えてください。