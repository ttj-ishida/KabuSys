KabuSys
=======

日本株向けの自動売買システム用ライブラリ（パイプライン基盤）。  
データ取得・スキーマ管理・戦略・発注・モニタリングのための基礎機能を提供します。

概要
----
KabuSys は日本株の自動売買に必要な基盤機能をまとめた Python パッケージです。  
主に次の要素を含みます。

- 環境変数ベースの設定管理（.env の自動読み込み機能付き）
- DuckDB を使った多層データスキーマの定義・初期化
- 戦略 / 発注 / モニタリング用の名前空間（拡張ポイント）

バージョン情報はパッケージトップで保持されています:
- kabusys.__version__ (例: "0.1.0")

主な機能
--------
- 環境変数の柔軟な読み込み
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数を保護）
  - export 形式、クォート、インラインコメント等に対応するパーサ
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 設定ラッパー Settings
  - J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等をプロパティで取得
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution の多層テーブル定義
  - 冪等な init_schema(db_path) でテーブルとインデックスを作成
  - get_connection(db_path) で接続を取得
- パッケージ構成（拡張点）
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

セットアップ手順
----------------
前提:
- Python 3.9+（型ヒントに Path | None などが使われているため）
- pip

1. リポジトリをクローン / 展開する
2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要な依存パッケージをインストール
   - 本リポジトリは DuckDB を使用しています。最低限以下をインストールしてください:
     ```
     pip install duckdb
     ```
   - 開発中は editable install を行うと便利です:
     ```
     pip install -e .
     ```
     （プロジェクトに pyproject.toml / setup.cfg がある場合）

環境変数 (.env)
----------------
プロジェクトルートに .env（および任意で .env.local）を配置します。自動で .env → .env.local の順に読み込まれます（.env.local が優先、既存の OS 環境変数は protected）。

必須の主なキー（Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN  — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD      — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack Bot Token
- SLACK_CHANNEL_ID       — 通知先 Slack Channel ID

オプション / デフォルト値:
- KABUS_API_BASE_URL     — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
- SQLITE_PATH            — デフォルト: data/monitoring.db
- KABUSYS_ENV            — development / paper_trading / live （デフォルト: development）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 (.env.example)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みを無効化する（テストなどで）
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# Windows (PowerShell):
# $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

使い方（簡単な例）
-----------------

1) 設定の参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.is_live)
```

2) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)   # テーブルとインデックスを作成して接続を返す

# 以降は conn.execute(...) でクエリ実行
print(conn.execute("SELECT count(*) FROM sqlite_master").fetchall())
```

3) メモリ内 DB を使う（テスト時など）
```python
conn = init_schema(":memory:")
# get_connection(":memory:") は別接続になるため、同じ接続オブジェクトを保持したい場合は init_schema を使う
```

注意点:
- get_connection() は既存 DB への接続を返すだけで、スキーマの初期化は行いません。初回は init_schema() を使ってください。

DuckDB スキーマ概要
-------------------
スキーマは 4 層で構成されています（DataSchema.md に準拠）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

さらに検索効率のためのインデックスが多数定義されています。init_schema() は冪等にテーブル／インデックスを作成します。

パッケージ構成（ファイルツリー）
-------------------------------
以下は主要ファイルとディレクトリの構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py           # パッケージ初期化、__version__, __all__
    - config.py             # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py           # DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - strategy/
      - __init__.py         # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py         # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py         # モニタリング関連（拡張ポイント）

拡張と開発
----------
- data/schema.py にあるテーブル設計をベースに、データ取得・加工ロジックを実装してください。
- strategy, execution, monitoring サブパッケージに機能を追加していく想定です。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。テスト環境等で CWD が異なる場合は注意してください。

ライセンス
---------
（プロジェクトのライセンス情報をここに記載してください）

サポート / 貢献
---------------
バグ報告や機能追加は Issue / Pull Request をお願いします。README に含めたい追加の使用例や運用手順があれば歓迎します。

以上。README の内容をプロジェクトの運用やドキュメントに合わせて調整してください。