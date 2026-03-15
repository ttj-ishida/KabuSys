# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）

このリポジトリは、データ収集・加工・特徴量生成・発注管理を想定した日本株自動売買基盤の骨組みを提供します。設定管理・DuckDB による永続化スキーマ・実行/戦略/モニタリング用のモジュール境界が含まれます。

## 機能一覧

- 環境変数・設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - 必須設定の明示的チェック（未設定だと例外）
  - 実行環境（development / paper_trading / live）とログレベル検証
- データベーススキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル作成・インデックス作成を行う `init_schema()`（冪等）
  - 既存 DB への接続を返す `get_connection()`
- モジュール領域（将来の拡張）
  - data: データ取得／スキーマ
  - strategy: 売買戦略
  - execution: 発注・約定管理
  - monitoring: モニタリング／アラート

## 動作要件

- Python 3.10+
  - （型注釈で `|` を使用しているため）
- duckdb Python パッケージ

必要に応じて他のパッケージ（Slack クライアントや API クライアント等）を追加してください。

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb
   # 開発用にパッケージとして編集可能インストール
   pip install -e .
   ```
   （requirements.txt がある場合はそれを利用してください）

4. 環境変数を設定
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   必須の環境変数（コード内で `_require` によりチェックされる）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意／デフォルトあり
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化
   - KABUSYS_API_BASE_URL 等の他の接続先は環境変数経由で上書き可能
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

   サンプル `.env`（例）
   ```
   JQUANTS_REFRESH_TOKEN=あなたのトークン
   KABU_API_PASSWORD=あなたのパスワード
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（簡単なコード例）

- 設定を参照する
```python
from kabusys.config import settings

# 必須値は設定されていなければ例外になる
token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

- DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回: スキーマ作成も含めて DB を初期化
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続するだけ
conn2 = get_connection(settings.duckdb_path)

# :memory: を渡すとインメモリ DB になる
mem_conn = init_schema(":memory:")
```

- 注意事項
  - init_schema() はテーブル／インデックス作成を行うため初回に呼ぶのが望ましい（冪等）。
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テストや CI で不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - settings.env / settings.log_level は値の検証を行うため、不正な値があると ValueError が発生します。

## DuckDB スキーマ概要

このパッケージはレイヤードアプローチでテーブルを用意します（`data/schema.py` に定義）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

主キー・チェック制約・インデックスが設計されており、データ整合性と検索性能を考慮しています。

重要な API:
- init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - ディレクトリが存在しない場合は自動作成。":memory:" も可。
- get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - スキーマ初期化は行わない。既存 DB に接続するために使用。

## ディレクトリ構成

（主要ファイルのみ抜粋）

```
src/
└── kabusys/
    ├── __init__.py
    ├── config.py                # 環境変数・設定管理
    ├── data/
    │   ├── __init__.py
    │   └── schema.py            # DuckDB スキーマ定義・初期化
    ├── strategy/
    │   └── __init__.py
    ├── execution/
    │   └── __init__.py
    └── monitoring/
        └── __init__.py
```

主要な公開 API（パッケージルート）:
- kabusys.config.settings
- kabusys.data.schema.init_schema, get_connection

## トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが検出されない（.git / pyproject.toml がない）場合、自動読み込みはスキップされます。手動で環境変数を設定するか、プロジェクトルートに .env を配置してください。
  - テスト実行時などで自動読み込みを無効にしている可能性があります（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB がインストールできない／接続エラー
  - Python のバージョンを確認（3.10+）。`pip install duckdb` を試してください。
- 必須環境変数が足りない
  - settings のプロパティアクセス時に ValueError が発生します。メッセージの指示に従って .env を作成してください。

---

上記 README はこのコードベースの現状（設定管理、DuckDB スキーマ定義、パッケージ骨格）に基づいています。戦略や実行の具体実装は将来的に追加する想定です。必要であれば README に CI／テスト手順や開発フロー（ブランチ戦略等）を追記できます。