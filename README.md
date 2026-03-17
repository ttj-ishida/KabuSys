KabuSys — 日本株自動売買基盤（README）
====================================

概要
----
KabuSys は日本株のデータ取得、品質チェック、特徴量作成、戦略・発注・監査までを想定した
自動売買プラットフォームのコアライブラリです。本リポジトリには主に以下の機能群が含まれます。

- J-Quants API からの株価（日次OHLCV）・財務データ・JPXマーケットカレンダー取得
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- マーケットカレンダー管理（営業日判定・前後営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ

設計上のポイント
- API レート制御・リトライ・トークン自動リフレッシュ実装（jquants_client）
- ETL は差分取得 + バックフィルで後出し修正に対応
- DB 操作は冪等（ON CONFLICT 等）を意識
- RSS 収集は SSRF / XML Bomb / 大容量レスポンス等の安全対策あり
- 品質チェックは Fail-Fast ではなく問題を集約して報告

機能一覧
--------
主要モジュールと提供機能（抜粋）:

- kabusys.config
  - 環境変数／.env 読み込み、自動ロードの仕組み（.env, .env.local）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN）

- kabusys.data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等性を保つ実装）
  - レートリミッタ・リトライ・トークン再取得実装

- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化関数 init_schema / get_connection

- kabusys.data.pipeline
  - run_daily_etl（カレンダー取得 → 株価ETL → 財務ETL → 品質チェック）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - RSS フィード取得（fetch_rss）
  - raw_news への保存（save_raw_news）、news_symbols の登録（save_news_symbols）
  - URL 正規化、記事ID生成、銘柄コード抽出、SSRF対策、受信サイズ制限等

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（JPX カレンダー夜間更新ジョブ）

- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合チェック
  - run_all_checks により QualityIssue のリストを返す

- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）初期化

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈に PEP 604 の union 型を使用しているため）
- pip が利用可能

1) 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存ライブラリのインストール（最小）
   - pip install duckdb defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

3) パッケージのインストール（編集可能モード）
   - pip install -e .

環境変数 / .env
- 自動で .env, .env.local をプロジェクトルートから読み込みます（優先順: OS 環境 > .env.local > .env）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabu ステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN        : Slack 通知を使う場合のボットトークン
- SLACK_CHANNEL_ID       : Slack 通知対象チャンネルID

その他（オプション）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視 DB 等（default: data/monitoring.db）

使い方（簡易例）
----------------

以下は Python スクリプト / REPL からの例です。実運用ではジョブスケジューラ（cron / Airflow 等）から呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")  # ファイル作成・テーブル作成
# またはインメモリでテスト: schema.init_schema(":memory:")
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) RSS ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # など
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

5) 監査テーブル（audit）を追加で初期化
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意点 / テスト用フック
- news_collector._urlopen はテストでモック可能（外部アクセスを差し替えられます）。
- jquants_client は内部でレート制御とリトライを持つため、大量ループで呼ぶ場合は考慮してください。
- .env パースはシェルライクな記法（export KEY=val、クォート、コメント）に対応しています。

ディレクトリ構成
----------------
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py               (パッケージ定義、__version__)
  - config.py                 (.env 読み込み・Settings)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント)
    - news_collector.py       (RSS 収集・保存)
    - schema.py               (DuckDB スキーマ定義・init)
    - pipeline.py             (ETL パイプライン)
    - calendar_management.py  (営業日判定・calendar 更新)
    - quality.py              (品質チェック)
    - audit.py                (監査ログスキーマ)
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

ドキュメント参照
- 各モジュール冒頭に設計方針・処理フローがコメントとして記載されています。
- .env.example をプロジェクトルートに用意しておくと環境構築が容易です（本リポジトリに同梱されている想定）。

ライセンス / コントリビュート
----------------------------
- 本 README ではライセンス情報は省略しています。実際のプロジェクトでは LICENSE を必ず追加してください。
- コントリビューションの手順（ブランチ戦略・PR ルール等）は別途 CONTRIBUTING.md を用意してください。

以上が本コードベースの概要と基本的な使い方です。詳細な API や運用フロー（発注ロジック・戦略設計・監視）は strategy / execution 層を実装して拡張してください。質問や補足があれば教えてください。