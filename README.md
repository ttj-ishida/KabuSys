# KabuSys

日本株自動売買システムの軽量コアライブラリ（プロトタイプ）

このリポジトリは、日本株の自動売買システムの基盤となるモジュール群を提供します。環境変数による設定管理、DuckDBによるオンディスク/インメモリデータベーススキーマ定義、戦略・実行・監視のためのパッケージ構成を含みます。

---

## 主要な特徴

- 環境変数ベースの設定管理（.env 自動読み込み）
  - .env / .env.local の順序で自動ロード（OS環境変数を尊重）
  - 必須キーが未設定の場合は明示的なエラーを投げる
- DuckDB を用いたスキーマ定義と初期化機能
  - Raw / Processed / Feature / Execution の多層データモデル
  - テーブル定義・インデックス、外部キー制約を含む冪等的な初期化
- モジュール分離
  - data（スキーマ・DB接続）
  - strategy（戦略関連：未実装のプレースホルダ）
  - execution（発注・取引管理：未実装のプレースホルダ）
  - monitoring（監視・ロギング：未実装のプレースホルダ）

---

## 必要条件

- Python 3.9+
- 必要ライブラリ（最低限）
  - duckdb

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# 開発インストール（パッケージ化されている場合）
# pip install -e .
```

実際のプロジェクトでは、他に HTTP クライアント、Slack SDK、J-Quants クライアントなどを追加で導入してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境の用意（上記参照）
3. 必要な環境変数を設定
   - 環境変数は OS 環境、またはプロジェクトルートの `.env` / `.env.local` に設定します。
   - 自動読み込みは、パッケージ内のファイルパスを起点にプロジェクトルート（.git または pyproject.toml）を探索して行われます。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト目的など）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルト
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

例: `.env`（プロジェクトルート）
```env
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

---

## 使い方

以下は主要な利用例です。

- 設定の参照
```python
from kabusys.config import settings

# 必須値は未設定だと ValueError が発生します
token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path に基づいてファイルの親ディレクトリを作成し、テーブルを作る
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 既存 DB への接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- 自動 .env 読み込みの制御
  - 通常、パッケージ読み込み時に .env/.env.local を自動で読み込みます。
  - テスト等で自動読み込みを無効化する場合:
    ```bash
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py           # パッケージのメタ情報 (version, __all__)
   ├─ config.py             # 環境変数・設定管理
   ├─ data/
   │  ├─ __init__.py
   │  └─ schema.py          # DuckDB スキーマ定義・初期化
   ├─ strategy/
   │  └─ __init__.py        # 戦略関連プレースホルダ
   ├─ execution/
   │  └─ __init__.py        # 発注/実行関連プレースホルダ
   └─ monitoring/
      └─ __init__.py        # 監視関連プレースホルダ
```

schema.py に定義されている主なテーブル（抜粋）
- Raw layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature layer: features, ai_scores
- Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックス定義も用意されており、一般的なクエリパターン（銘柄×日付スキャン、ステータス検索）に最適化されています。

---

## 注意事項 / 補足

- 現状のリポジトリはコアの骨組みであり、戦略実装・発注処理・監視ロジックなどは各プロジェクトで実装する想定です。
- 環境変数のパースロジックは POSIX 風の .env 形式にかなり忠実です（export プレフィックス、引用符、エスケープ、コメント処理等を考慮）。
- DuckDB の初期化は冪等（既に存在するテーブルやインデックスはスキップ）なので、何度でも安全に実行できます。
- データベースパスに ":memory:" を渡すとインメモリの DuckDB を使えます（テスト等に便利）。

---

もし README に追加したい情報（例: 実際の戦略テンプレート、発注フロー図、CI の設定、依存パッケージの完全な一覧など）があれば教えてください。必要に応じてサンプルコードや運用ガイドも作成します。