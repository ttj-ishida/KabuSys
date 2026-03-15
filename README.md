# KabuSys

日本株向けの自動売買システム (KabuSys) の軽量ライブラリ（初期版: 0.1.0）

このリポジトリは市場データ管理、特徴量・AIスコアの格納、発注／約定管理などを行うための基盤的なモジュール群を提供します。DuckDB を用いたスキーマ定義や、環境変数ベースの設定読み込み機能を備えています。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数
- セットアップ手順
- 使い方
  - 設定の読み込み
  - DuckDB スキーマ初期化
  - 既存 DB への接続
- ディレクトリ構成
- 補足・注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークの基盤モジュールです。  
主に次を目的とします。

- 生データから加工済みデータ、特徴量、AIスコア、発注・約定・ポジションなどを格納する DuckDB スキーマの提供
- 環境変数（.env / .env.local / OS 環境）による設定管理（自動読み込み）
- 将来的なストラテジー、発注、モニタリング等の拡張ポイントを想定したパッケージ構成

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理
  - プロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込み（無効化可能）
  - クォート／エスケープ、コメントのパース対応
  - 必須変数未設定時はエラーを投げるヘルパー（settings）

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution の 4 層のテーブル定義
  - インデックス定義（頻出クエリを想定）
  - init_schema(db_path) で冪等にテーブル／インデックスを作成
  - get_connection(db_path) で既存 DB に接続

- 設定プロパティ（Settings）
  - J-Quants / kabuステーション / Slack / DB パス / 環境フラグ（development/paper_trading/live）など

---

## 必要な環境変数

必須（アプリ起動や一部機能で必須）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（デフォルト: development） — 有効値: development, paper_trading, live
- LOG_LEVEL（デフォルト: INFO） — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

特記事項:
- .env と .env.local はプロジェクトルート（.git または pyproject.toml を基準）から読み込まれます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト目的など）。

簡易的な .env 例:
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python をインストール（推奨: 3.9+）
2. リポジトリをクローン／配置
3. 依存パッケージ（最低限 DuckDB）
   - pip で duckdb をインストール:
     ```
     pip install duckdb
     ```
   - 実際の環境では slack-sdk や各 API クライアント等を必要に応じて追加してください（本リポジトリのコードは最小限の依存のみを含みます）。

4. 環境変数を用意
   - プロジェクトルートに .env を作成するか、OS 環境変数として設定する
5. (任意) 仮想環境を有効化し、パッケージをインストール:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   pip install -r requirements.txt  # requirements.txt がある場合
   ```

---

## 使い方

以下は基本的な使用例です。

- 設定値の取得（settings）
```python
from kabusys.config import settings

# 必須環境変数が未設定の場合、アクセス時に ValueError が発生します
token = settings.jquants_refresh_token
print("KabuSys environment:", settings.env)
print("DuckDB path:", settings.duckdb_path)
```

- DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema

# デフォルトパスを使う場合は settings.duckdb_path を利用
conn = init_schema(settings.duckdb_path)  # 指定したパスに DB を作成し、全テーブルを作成して接続を返す
# conn は duckdb.DuckDBPyConnection
```

- インメモリ DB を使う（テスト等）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- 既存 DB への接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みを無効化する（テストなど）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python your_app.py
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル（コードベースから抜粋）:

- src/kabusys/
  - __init__.py              — パッケージ初期化, __version__ = "0.1.0"
  - config.py                — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・init_schema / get_connection
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要なテーブル（schema.py に定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスも複数定義されています（例: idx_prices_daily_code_date, idx_signal_queue_status ...）。

---

## 補足・注意点

- init_schema は冪等（既に存在するテーブルは作成しない）です。初回のみ呼び出してスキーマを整備してください。
- .env のパースはクォートやエスケープ、コメントに対応していますが、複雑なケースは確認してください。
- KABUSYS_ENV は動作モードに応じて `development` / `paper_trading` / `live` を指定します。`is_live` / `is_paper` / `is_dev` プロパティで判定できます。
- 本リポジトリは基盤モジュールに限定されており、実際の発注実行ロジックや Slack 通知の実装、各種 API クライアントは別途実装が必要です。

---

必要であれば、README に以下を追記できます:
- requirements.txt の例
- データ投入・マイグレーション手順
- API や CLI の使用例（拡張モジュール実装時）