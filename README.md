# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム基盤です。市場データ取得・整形、特徴量生成、シグナルと発注の管理までを見据えたデータ層・実行層のスキーマや、環境設定の取り扱いを提供します。現時点ではコアとなる設定・スキーマ定義が実装されています（戦略・実行エンジンは拡張可能なパッケージ構成）。

---

## 概要

- 環境変数による設定管理（.env/.env.local 自動ロード、細かいパース仕様を実装）
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
- スキーマ初期化用 API（冪等的にテーブル・インデックスを作成）
- KABUSYS_ENV による実行モード判定（development / paper_trading / live）
- 将来的な戦略（strategy）・実行（execution）・監視（monitoring）用パッケージ構成

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - export 形式やクォート、エスケープ、コメントの扱いに対応した .env パーサー
  - 必須キー未設定時は ValueError を送出する Settings API
  - 環境変数の優先順位: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw 層（raw_prices, raw_financials, raw_news, raw_executions）
  - Processed 層（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
  - Feature 層（features, ai_scores）
  - Execution 層（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 頻出クエリを考慮したインデックス作成
  - init_schema(db_path) によりディレクトリ自動作成＋テーブル作成（冪等）
  - get_connection(db_path) で既存 DB に接続

---

## 前提・準備

- Python 3.10 以上（型ヒントで「X | Y」構文を使用）
- pip が使用可能であること
- DuckDB（Python パッケージ）が必要

推奨: 仮想環境を作成してからインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install duckdb
# またはプロジェクト配布パッケージがある場合:
# python -m pip install -e .
```

（requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## 環境変数（.env）

プロジェクトは以下の主要な環境変数を参照します。必須のものは Settings プロパティで _require され、未設定時は ValueError が発生します。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
  - kabuステーション API のベース URL
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack 送信先チャネル ID
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルのパス（:memory: を指定するとインメモリ DB）
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
  - 監視用 SQLite ファイルパス（将来の用途想定）
- KABUSYS_ENV (省略可, デフォルト: development)
  - 実行環境。使用可能値: development, paper_trading, live
- LOG_LEVEL (省略可, デフォルト: INFO)
  - ログレベル。使用可能値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD (省略可)
  - "1" をセットすると .env 自動ロードを無効化（テスト等で利用）

例 (.env):
```
JQUANTS_REFRESH_TOKEN='your-jquants-refresh-token'
KABU_API_PASSWORD='your-kabu-password'
SLACK_BOT_TOKEN='xoxb-...'
SLACK_CHANNEL_ID='C01234567'
DUCKDB_PATH='data/kabusys.duckdb'
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- ファイル読み込み順は .env → .env.local（.env.local が上書き）ですが、OS 環境変数は常に保護されます（上書きされません）。
- .env のパースはシェル形式に近い挙動を実装しており、クォートやバックスラッシュエスケープ、コメントを考慮します。

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成・依存パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# またはプロジェクト定義に従う:
# pip install -e .
```

3. プロジェクトルートに .env を作成（上記の環境変数参照）
- 必須キー(JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) を設定してください。

4. DuckDB スキーマを初期化
（下記「使い方」参照）

---

## 使い方（主要 API）

- Settings（環境設定の利用）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.env, settings.is_dev, settings.is_live)
```

- スキーマの初期化（DuckDB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# 設定されたパスに対してスキーマを初期化（ディレクトリ自動作成）
conn = init_schema(settings.duckdb_path)

# インメモリ DB で試す場合
conn_mem = init_schema(":memory:")
```

- 既存 DB へ接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- スキーマ初期化の動作
  - 全テーブル（Raw / Processed / Feature / Execution）とインデックスを作成します。
  - 既に存在するオブジェクトはスキップするため冪等です。
  - DB ファイルの親ディレクトリが存在しない場合は自動作成します。

---

## ディレクトリ構成

（主要ファイル・モジュール）
```
src/
  kabusys/
    __init__.py              # パッケージ定義（__version__=0.1.0）
    config.py                # 環境変数・設定管理（Settings）
    data/
      __init__.py
      schema.py              # DuckDB スキーマ定義・初期化 API
    strategy/
      __init__.py            # 戦略モジュール（拡張ポイント）
    execution/
      __init__.py            # 発注/実行モジュール（拡張ポイント）
    monitoring/
      __init__.py            # 監視用モジュール（拡張ポイント）
```

ファイルの役割（抜粋）:
- src/kabusys/config.py
  - .env 自動ロード、環境変数取得用 Settings クラスを提供
- src/kabusys/data/schema.py
  - DuckDB の DDL 定義（多層テーブル）と init_schema / get_connection を提供
- strategy/ execution/ monitoring/
  - 将来的な戦略・実行・監視の実装を追加するためのパッケージ

---

## 注意点・トラブルシューティング

- 必須の環境変数が未設定だと Settings のプロパティアクセス時に ValueError が発生します。ログや例外を見て .env を確認してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト環境などで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に接続できない／ファイルが作成できない場合はファイルパスの権限や親ディレクトリの存在を確認してください。init_schema は親ディレクトリを自動作成しますが、OS 権限により失敗することがあります。
- .env のパース挙動はシェルライクですが完全なシェル互換ではありません。クォート・エスケープを含めた値を使用する場合は注意してください。

---

## 拡張案（今後の作業）

- 実際のデータ取得（J-Quants、ニュース、kabu API）を実装するクライアント
- strategy パッケージに戦略実装・バックテスト機能
- execution パッケージに発注ロジック、kabuステーション連携
- monitoring にダッシュボードや通知・アラート実装

---

この README は現状のコードベース（設定管理と DuckDB スキーマ）に基づいて作成しています。追加の機能や API を実装した際は README を更新してください。