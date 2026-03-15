# KabuSys

日本株向けの自動売買システム基盤ライブラリ（開発中）
バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買アプリケーションを構築するための基盤モジュール群です。データの保存・スキーマ定義（DuckDB）、環境変数管理、設定取得のユーティリティを提供します。戦略（strategy）や発注（execution）、監視（monitoring）といった領域を想定したパッケージ構成になっています。

主な特徴
-------
- 環境変数自動読み込み（.env / .env.local → OS環境変数優先）
- アプリケーション設定クラス（Settings）で必要な設定値を型安全に取得
- DuckDB 用スキーマ定義と初期化ユーティリティ（init_schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
- モジュール化されたパッケージ構成（data, strategy, execution, monitoring）

必要条件
-------
- Python 3.10 以上
- duckdb Python パッケージ

セットアップ手順
--------------
1. リポジトリをクローン／コピー

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb

   （プロジェクトが pip 化されていれば pip install -e . 等でインストール）

4. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local があればそれを優先して上書き）。
   - 自動読み込みを無効化したい場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで使用）。

.env 例（必須キーの例）
---------------------
以下は最低限必要なキーの例です（実際のトークンや ID は適切に設定してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

任意/デフォルト設定例：
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_DISABLE_AUTO_ENV_LOAD=0

環境変数の読み込み仕様（補足）
-----------------------------
- プロジェクトルートは config.py の位置から上に向かって .git または pyproject.toml を探索して決定します。見つからない場合は自動読み込みをスキップします。
- 読み込み順序: OS環境変数 > .env.local > .env
- .env の解析はシェル風の簡易パーサーで、クォート、エスケープ、行末コメントなどに対応しています。
- OS 環境変数は .env/.env.local によって上書きされません（上書きを許可する保護除外の仕組みあり）。

使い方（短いサンプル）
--------------------

1) 設定を取得する（Settings）
```python
from kabusys.config import settings

# 必須キーに未設定があれば ValueError が発生します
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)  # デフォルト: http://localhost:18080/kabusapi
print(settings.env)                # development / paper_trading / live
```

2) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

3) 既存 DB に接続する
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

スキーマの概要
--------------
DuckDB のテーブルは以下のレイヤーで設計されています（主なテーブル）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

多くのテーブルにプライマリキーや制約、頻出クエリ用のインデックスが設定されています。init_schema() は冪等的にテーブルを作成します（存在すればスキップ）。

設定（Settings）で要求される主な環境変数
-------------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)

開発・テスト時のヒント
-------------------
- 自動環境読み込みを無効にするには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env/.env.local の書式はシェル風ですが、厳密な shell パーサーではありません。クォートとバックスラッシュの基本的な扱いに対応しています。

ディレクトリ構成
--------------
プロジェクトの主要な配置（抜粋）:

src/
  kabusys/
    __init__.py                # パッケージ定義、__version__ = "0.1.0"
    config.py                  # 環境変数読み込み・Settings
    data/
      __init__.py
      schema.py                # DuckDB スキーマ定義・init_schema/get_connection
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。プロジェクトに合わせて LICENSE を追加してください。）
コントリビューションや issue、PR に関してはリポジトリの CONTRIBUTING.md や issue テンプレートを参照してください。

最後に
-----
この README は現状のコードベース（設定管理とスキーマ初期化周り）を説明するものです。戦略ロジックや発注実装、監視機能は各パッケージ（strategy, execution, monitoring）へ実装を進める想定です。必要であればサンプル戦略や運用手順の追記も対応します。