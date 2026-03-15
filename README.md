KabuSys
=======

KabuSys は日本株向けの自動売買基盤のコアライブラリです。本リポジトリは環境変数管理、データ層（DuckDB）スキーマ定義、戦略／実行／モニタリングのためのパッケージ骨組みを提供します（現状は主に設定と DB 初期化部分が実装されています）。

主な特徴
--------
- 環境変数／設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（.git または pyproject.toml を基準に探索）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - 複雑な .env のパース（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理）に対応
  - 必須設定を取得すると ValueError を投げる簡易 Settings クラスを提供

- DuckDB ベースのデータスキーマ（初期化機能）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル群（価格、財務、ニュース、シグナル、オーダー、トレード、ポジション、ポートフォリオ等）を表現
  - 必要なインデックスも作成（頻出クエリを想定）
  - init_schema(db_path) で冪等にスキーマを初期化し接続を返す API、get_connection() で既存 DB への接続取得

- 設定値のバリデーション
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）

機能一覧
--------
- 自動 .env ロード（プロジェクトルート検出）
- .env の堅牢なパースロジック
- Settings クラス経由での設定取得（J-Quants、kabu API、Slack、データベースパス、ランタイム設定 など）
- DuckDB スキーマ定義と初期化（init_schema）
- get_connection による接続取得
- スキーマは以下の層とテーブルを含む（主なもの）
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

セットアップ手順
--------------
1. Python 環境を用意
   - 推奨: Python 3.9+（プロジェクトの pyproject.toml があればそちらに合わせてください）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - まず最低限 duckdb が必要です:
     - pip install duckdb
   - その他、kabu API や Slack 連携の実装を追加する場合はそれらのクライアントを追加してください。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を配置します。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.example の .env テンプレート（例）
---------------------------------
以下は必要なキーの例です（実際の値は各自で設定してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略可能（デフォルト: http://localhost:18080/kabusapi）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時のデフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境: development | paper_trading | live
KABUSYS_ENV=development

# ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

- Settings を使う（環境変数の取得）

Python:

from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError
print(settings.kabu_api_base_url)      # デフォルト http://localhost:18080/kabusapi
print(settings.duckdb_path)            # Path オブジェクトを返す

- DuckDB スキーマを初期化して接続を取得する

from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# スキーマを作成（ファイルがなければディレクトリを自動作成）
conn = init_schema(settings.duckdb_path)

# 以後 conn を使って SQL を実行
with conn:
    rows = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
    print(rows)

# 既存 DB に接続するだけなら
conn2 = get_connection(settings.duckdb_path)

- 自動 .env ロードの無効化（テストなどで）
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからパッケージを読み込むと .env 読み込みを行いません。

注意点・実装メモ
----------------
- .env のパースは次のようなケースに対応しています:
  - export KEY=val
  - KEY='value with spaces and \'escaped\' chars'
  - KEY="value with \"escaped\" chars"
  - VALUE # comment（直前にスペースまたはタブがある場合のみコメントとして扱う）
- Settings のプロパティは必須値を _require() で取得します。必須環境変数が未設定だと ValueError を投げます。
- DuckDB のスキーマ初期化は冪等です（既存テーブルは上書きされません）。
- init_schema は ":memory:" を指定するとインメモリ DB を使用します。

ディレクトリ構成
---------------
リポジトリ内の主要なファイル構成（抜粋）:

src/
  kabusys/
    __init__.py               # パッケージ公開 (version, __all__)
    config.py                 # 環境変数・設定管理
    data/
      __init__.py
      schema.py               # DuckDB スキーマ定義と init_schema / get_connection
    strategy/
      __init__.py             # 戦略関連モジュール（骨組み）
    execution/
      __init__.py             # 発注・実行関連モジュール（骨組み）
    monitoring/
      __init__.py             # モニタリング関連（骨組み）

その他
-----
- スキーマの詳細（DataSchema.md）に基づいてテーブル定義をしています。DataSchema.md があれば参照してください。
- 本パッケージは骨組み段階の実装が中心です。実際の取引ロジック、API クライアント、Slack 通知などは別途実装・統合してください。

貢献
----
バグ報告、改善提案や機能追加のプルリクエスト歓迎です。まず Issue を作成してください。

ライセンス
----------
（プロジェクトに合わせて適宜記載してください）