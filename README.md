# KabuSys

日本株向けの自動売買システム用ライブラリ（初期段階）
パッケージ名: `kabusys`  
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ管理、特徴量生成、シグナル管理、発注/約定/ポジション管理を想定した内部ライブラリ群を提供します。  
主な目的は以下です。

- 市場データ・ファンダメンタル・ニュース・実行履歴などのデータを DuckDB に格納するスキーマ管理
- 簡易な環境設定（.env / 環境変数）管理
- 戦略・実行・監視モジュールのための基盤（パッケージ骨組み）

現状はスキーマ定義や設定周りが実装されています。戦略・実行・監視ロジックは各サブパッケージ（骨組み）として用意されています。

---

## 機能一覧

- 環境変数/設定の自動読み込み
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（優先順位: OS > .env.local > .env）
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能
  - `export KEY=val` 形式やクォート（シングル/ダブル）のエスケープを考慮したパーサ実装
- 設定アクセスラッパー `kabusys.config.settings`
  - J-Quants, kabu API, Slack, DB パス、実行環境フラグ（development / paper_trading / live）など
- DuckDB 用スキーマ定義 & 初期化
  - Raw / Processed / Feature / Execution の 3〜4 層構造テーブルを定義
  - インデックスと外部キー、CHECK 制約を含んだDDL群
  - 初期化関数 `init_schema(db_path)` と既存接続取得 `get_connection(db_path)`

主要テーブル例（抜粋）:
- Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
- Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
- Feature: `features`, `ai_scores`
- Execution: `signals`, `signal_queue`, `orders`, `trades`, `positions`, `portfolio_performance`

---

## セットアップ手順

1. Python 環境（3.10+ 推奨）を用意します。

2. 依存パッケージのインストール（最低限）
   - duckdb
   - 例: pip を使用する場合
     pip install duckdb

3. リポジトリをクローン / ソースを配置し、パッケージをインポートできるようにします（開発時）
   - プロジェクトルートに `pyproject.toml` や `.git` があると、自動で .env 読み込みのルートが決まります。

4. 環境変数の設定
   - OS 環境変数かプロジェクトルートの `.env` / `.env.local` を作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
     - LOG_LEVEL (default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

5. データベーススキーマの初期化
   - `kabusys.data.schema.init_schema()` を呼んで DuckDB ファイルを初期化します（親ディレクトリがなければ自動作成）。

---

## 使い方（簡易例）

- 環境変数の読み込みと設定参照

```python
from kabusys.config import settings

# 必須値が未設定の場合は ValueError が発生します
token = settings.jquants_refresh_token
print("実行環境:", settings.env)
print("ライブモードか:", settings.is_live)
```

- DuckDB スキーマ初期化と接続取得

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイルパスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# またはインメモリ
# conn = init_schema(":memory:")

# 以降 conn.execute(...) でクエリ実行可能
# 既存 DB に再接続するだけなら get_connection を使用
conn2 = get_connection(settings.duckdb_path)
```

- .env のサンプル（プロジェクトルートに配置）

```
# .env (例)
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
SLACK_BOT_TOKEN="xoxb-xxx"
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- 自動 .env 読み込みを無効化する（テスト等）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## .env パーサの挙動（概要）

- コメント行（先頭が `#`）は無視
- `export KEY=val` 形式に対応
- 値がクォート（シングル/ダブル）の場合はクォートを考慮し、バックスラッシュエスケープを処理（閉じクォートまでを値として採る）
- クォートが無い場合、値内の `#` は直前がスペース or タブ の場合にコメントとみなす（通常の inline comment 対応）
- 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
- 読み込み時に OS の既存環境変数は保護される（.env による上書きを防止）。ただし `.env.local` は override=True で上書きされるが、OS の環境変数は保護される。

---

## ディレクトリ構成

プロジェクト内の主要ファイル（抜粋）:

src/
  kabusys/
    __init__.py               # パッケージ定義（__version__ = "0.1.0"）
    config.py                 # 環境変数・設定管理（自動 .env 読み込み、Settings クラス）
    data/
      __init__.py
      schema.py               # DuckDB スキーマ定義 & init_schema / get_connection
    strategy/
      __init__.py             # 戦略関連モジュール（空の初期化）
    execution/
      __init__.py             # 発注/実行関連（空の初期化）
    monitoring/
      __init__.py             # 監視・モニタリング関連（空の初期化）

説明:
- `config.py` が設定管理の中核で、`settings` インスタンスを介して環境変数を取得します。
- `data/schema.py` が DB スキーマ定義の全容を保持し、初期化 API を提供します。
- `strategy`, `execution`, `monitoring` は今後の実装領域として用意されています。

---

## 補足・運用上の注意

- `init_schema()` は冪等（既に存在するテーブルは作成しない）なので、複数回安全に呼べます。
- デフォルトの DB パス（`data/kabusys.duckdb`）はプロジェクト下に作成されます。運用環境では十分なバックアップ・管理をしてください。
- `Settings` のいくつかのプロパティは未設定時に ValueError を送出するため、必須環境変数の設定を忘れないでください。

---

必要であれば README に以下を追加できます:
- 詳細な .env.example の完全版
- DuckDB テーブルのカラム説明ドキュメント（DataSchema.md 相当）
- 開発・テストの手順（ユニットテスト、CI 設定）