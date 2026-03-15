# KabuSys

日本株向けの自動売買システム基盤（ライブラリ）です。データ収集・スキーマ定義、環境設定管理、取引戦略・発注・監視用のモジュール群を提供することを目的としています（現状はスキーマ定義・設定まわりが実装済み）。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下の要素を備えた自動売買プラットフォームの骨組みを提供します。

- 環境変数・設定の読み込みと管理（.env 自動読み込み対応）
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
- 将来的に戦略（strategy）、発注（execution）、監視（monitoring）モジュールを統合可能なパッケージ構成

現在の実装では、環境設定管理（`kabusys.config`）と DuckDB スキーマ初期化（`kabusys.data.schema`）が利用可能です。戦略・実行・監視用のパッケージはプレースホルダとして存在します。

---

## 主な機能

- 環境変数管理
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込み
  - export 形式、クォート、インラインコメントに対応したパーサー
  - 必須環境変数未設定時に例外を投げるヘルパー（`Settings`）
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義（テーブル & インデックス）
  - スキーマ初期化関数 `init_schema(db_path)`（冪等・親ディレクトリ自動作成）
  - 既存 DB への接続取得 `get_connection(db_path)`

---

## セットアップ手順

前提: Python 3.10 以上（型ヒントで `X | None` などを使用しているため）

1. 仮想環境（任意）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. パッケージのインストール
   - 最小依存:
     - pip install duckdb
   - 開発中にパッケージとして扱う場合（プロジェクトルートに pyproject.toml または setup.cfg がある想定）:
     - pip install -e .
   - その他、Slack 連携等を使う場合は該当ライブラリ（slack-sdk など）を追加でインストールしてください。

3. .env の準備
   - プロジェクトルートに `.env`（と任意で `.env.local`）を作成してください。
   - 必須キーの例（README に例を記載）を設定してください。

4. 自動環境読み込みを無効化したい場合（テスト等で）:
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必須 / 推奨環境変数（.env 例）

基本的に以下の環境変数が参照されます。必須のものは `Settings` 内で未設定時に例外が発生します。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は未設定時は http://localhost:18080/kabusapi が既定値
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb      # 任意（デフォルト）
SQLITE_PATH=data/monitoring.db       # 任意（デフォルト）
KABUSYS_ENV=development              # 有効値: development, paper_trading, live
LOG_LEVEL=INFO                       # 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意:
- 自動読み込み順序は OS 環境 > .env.local > .env です。`.env.local` は `.env` を上書きします。
- `.env` のパースは export 形式、クォート、インラインコメント（スペースのある # はコメント）に対応しています。

---

## 使い方（簡単な例）

1) バージョン確認
from kabusys import __version__
print(__version__)

2) 設定値の取得
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.duckdb_path)  # Path オブジェクト

3) DuckDB スキーマ初期化
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection。通常の duckdb 操作が可能
with conn:
    conn.execute("SELECT count(*) FROM prices_daily").fetchall()

4) 既存 DB へ接続（スキーマ初期化を行わない）
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)

5) 自動 .env 読み込みを無効にして明示的に .env を読み込みたい場合
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後、任意の .env ローダーを使うか、手動で os.environ を設定してください。

---

## ディレクトリ構成

以下は現在のパッケージ構成（主要ファイルのみ）です。

src/
  kabusys/
    __init__.py                # パッケージ定義、__version__ 等
    config.py                  # 環境変数/設定管理（自動 .env 読み込み、Settings クラス）
    data/
      __init__.py
      schema.py                # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    strategy/
      __init__.py              # 戦略関連（プレースホルダ）
    execution/
      __init__.py              # 発注/実行関連（プレースホルダ）
    monitoring/
      __init__.py              # 監視・ログ・メトリクス（プレースホルダ）

主な実装箇所:
- kabusys.config: 自動 .env 読み込みロジック（.git / pyproject.toml を基準にプロジェクトルートを探索）、パーサー、Settings（プロパティによる安全な取得）
- kabusys.data.schema: DuckDB の DDL（多層スキーマ）とインデックス、init_schema/get_connection

---

## 実装上のポイント・注意事項

- Python 3.10 以上を想定しています（構文上の都合）。
- .env 自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml を探索）。配布後や CWD が異なる状況でも振る舞いを安定させるための実装です。
- init_schema は冪等に設計されています。既存テーブルがあればスキップされます。
- 必要な外部ライブラリ: duckdb （DB 初期化・接続で使用）
- strategy / execution / monitoring モジュールは現状プレースホルダです。実際の戦略ロジック・発注処理を統合する際はこれらに実装を追加してください。

---

## 今後の拡張案（例）

- J-Quants / kabu API クライアント実装
- Slack 通知や監視アラート機能の実装
- 戦略定義API（信号生成 → キュー → 発注ワークフロー）
- バックテスト用のユーティリティ（過去データを使ったパフォーマンス計測）
- テストと CI（自動テスト、型チェック、Lint）

---

必要に応じて .env.example の作成、依存パッケージを列挙した requirements.txt / pyproject.toml の整備を行ってください。質問や追加で記載したい情報があれば教えてください。