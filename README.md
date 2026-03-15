# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ/パッケージ骨組み）。  
このリポジトリはデータ管理（DuckDBスキーマ）、環境設定の読み込み、戦略／実行／モニタリング用パッケージの土台を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの共通ライブラリです。  
主な目的は次のとおりです。

- 環境変数や .env ファイルからの設定管理（自動ロード機能付き）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）用スキーマ定義と初期化
- 戦略（strategy）, 発注/実行（execution）, モニタリング（monitoring）のためのパッケージ構造

このリポジトリはコア部分のみを包含しており、各コンポーネント（データ収集、モデル、実行ロジック等）は別途実装します。

---

## 機能一覧

- 環境変数/`.env` 読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込み
  - `export KEY=val` 形式、クォート付き値、エスケープ、インラインコメントの一部ルールに対応
  - `.env.local` は `.env` を上書き（ただし OS 環境変数は保護）
  - 自動読み込みを無効にする環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 設定アクセス用オブジェクト `kabusys.config.settings`
  - 必須変数は取得時に未設定なら例外を投げる
  - ヘルパープロパティ（env判定、ログレベルなど）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル DDL を提供
  - インデックス定義を含む冪等な初期化関数 `init_schema`
  - 既存 DB に接続する `get_connection`
- パッケージ構成（strategy / execution / monitoring）の雛形を提供

---

## 要件

- Python 3.10 以上（型注釈や union 型演算子 (`|`) に依存）
- duckdb Python パッケージ

例（開発環境に導入する最小コマンド）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
# パッケージを editable インストールする場合
python -m pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python と依存パッケージ（少なくとも duckdb）をインストール
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成
   - `.env.example` を参考に環境変数を設定してください（プロジェクトに例ファイルがない場合は下記を参照）
4. DuckDB スキーマを初期化（下記「使い方」を参照）

推奨される環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack 送信先チャネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

○ 自動読み込みの挙動：
- パッケージ読み込み時に、実行環境の OS 環境変数が優先されます（保護）
- プロジェクトルートが見つからない場合は自動ロードをスキップ
- 自動ロードを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

---

## 使い方

基本的な使い方例を示します。

- 設定の取得
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.env, settings.log_level)
```

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- メモリ内 DB（テスト用）
```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
```

- 既存 DB に接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- .env 自動読み込みを無効化してから設定を手動でロードする（テストなど）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```
あるいは Python 内から環境を操作してから import すること（注意: パッケージ import 後は自動ロード済みの可能性があります）。

スキーマには以下の層が定義されています（主要テーブルの例）:
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_performance

各テーブルは外部キー・インデックスを含み、初期化は冪等（既存テーブルは上書きしません）。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（パッケージルートは `src/kabusys`）

- src/kabusys/
  - __init__.py
    - パッケージメタ情報（__version__）とエクスポート一覧
  - config.py
    - 環境変数・設定管理（自動 .env ロード、settings オブジェクト）
  - data/
    - __init__.py
    - schema.py
      - DuckDB の DDL 定義、init_schema()、get_connection()
  - strategy/
    - __init__.py
    - （戦略実装を置く場所）
  - execution/
    - __init__.py
    - （発注 / 注文管理の実装を置く場所）
  - monitoring/
    - __init__.py
    - （監視 / メトリクス等の実装を置く場所）

プロジェクトルートには通常 `.env`, `.env.local`, pyproject.toml または .git が存在し、それらを基準に自動 .env 検出を行います。

---

## 補足・注意事項

- settings の必須プロパティに未設定でアクセスすると `ValueError` が発生します。`.env` が正しくセットされているか確認してください。
- `.env.local` は `.env` を上書きしますが、実行環境の OS 環境変数（既にセットされているキー）は保護され上書きされません。
- DuckDB のパスに `:memory:` を渡すとインメモリ DB を使用します（テスト用に便利）。
- Python のバージョン要件に注意してください（3.10 以上推奨）。

---

必要があれば、README に以下の追加を作成できます：
- .env.example のテンプレート
- より詳細な DB クエリ/サンプルスクリプト
- strategy / execution の実装ガイドライン

要望があれば追記します。