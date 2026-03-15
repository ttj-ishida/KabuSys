# KabuSys

日本株向け自動売買システム（ライブラリ）です。  
データ収集・加工（Raw / Processed / Feature 層）、特徴量管理、発注・取引履歴管理のためのスキーマと設定管理を提供します。

バージョン: 0.1.0

## 主な特徴
- 層構造のデータベーススキーマ（Raw / Processed / Feature / Execution）
- DuckDB を使ったローカルデータベースの自動初期化（冪等）
- 環境変数 / .env ファイルからの設定読み込み（自動ロード）
- アプリケーション設定をラップした Settings オブジェクト（必須キーの検証含む）
- 発注・約定・ポジション管理用テーブルとインデックス定義
- モジュール分割（data, strategy, execution, monitoring）による拡張しやすい構成

## 必要条件
- Python 3.10+
- duckdb Python パッケージ

例:
pip install duckdb

（プロジェクトをパッケージ化している場合は pip install -e . 等でも可）

## セットアップ手順

1. リポジトリをクローン / コピーします。

2. 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール:
   pip install duckdb

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

必須の環境変数（Settings が参照する）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルト:
- KABUSYS_ENV: 開発環境を示す。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL: `INFO`（デフォルト） 等
- KABU_API_BASE_URL: デフォルト `http://localhost:18080/kabusapi`
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`

例: `.env`（簡易）
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO

.env の読み込みルール（概略）:
- 優先順位: OS 環境変数 > .env.local > .env
- export キーワードやクォート（' / "）に対応
- コメント処理はクォートや先行空白を考慮したパース処理が行われます

## 使い方（簡単な例）

- 設定の参照:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

- DuckDB スキーマの初期化:
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は Path を返します（デフォルト data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)

  # メモリ上 DB を使いたい場合:
  conn = init_schema(":memory:")

  init_schema() はテーブルが既に存在する場合にスキップするため冪等です。親ディレクトリがなければ自動作成します。

- 既存 DB への接続:
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

- DB 内の操作は DuckDB の通常 API を利用できます:
  conn.execute("SELECT * FROM prices_daily LIMIT 10").fetchall()

## ディレクトリ構成

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings クラス）
  - data/
    - __init__.py
    - schema.py              — DuckDB のテーブル定義・初期化（init_schema, get_connection）
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注・実行モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            — モニタリング関連（拡張ポイント）

主要ファイルの説明:
- config.py: .env 自動読み込み機能、必須・選択環境変数のラッパー（settings）
- data/schema.py: Raw / Processed / Feature / Execution の各テーブル DDL を定義。init_schema() で一括作成。
  - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤ: features, ai_scores
  - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ用にインデックス定義あり

## 注意点 / 追加情報
- Settings の各プロパティは未設定の必須変数を参照した場合に ValueError を送出します（例: JQUANTS_REFRESH_TOKEN が未設定の場合）。
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。ルートが特定できない場合は自動ロードをスキップします。
- schema の DDL はチェック制約（チェック・NOT NULL・外部キーなど）を含んでいます。アプリケーション側ではこれら制約を前提にしたデータ操作を行うことが望ましいです。

---

拡張や実運用にあたっては、strategy / execution / monitoring の各モジュールを実装し、シグナル生成 → signal_queue 登録 → 注文作成のフローを構築してください。README に記載の Settings と init_schema を利用することで、設定・データ基盤の初期化は容易に行えます。