KabuSys
=======

日本株向けの自動売買プラットフォーム向けユーティリティ群。  
データ取得（J-Quants）、DuckDB スキーマ定義・初期化、監査ログ、データ品質チェック、環境変数管理など、ETL〜特徴量生成〜発注監査までの土台機能を提供します。

主な特徴
-------
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を考慮したスロットリング
  - リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ対応
  - データ取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
- DuckDB スキーマ設計・初期化
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - インデックスや外部キー制約を含む冪等な初期化
- 監査ログ（audit）
  - シグナル〜発注〜約定まで UUID 連鎖でトレース可能な監査テーブル群
  - 冪等キー（order_request_id）や各種ステータス管理
- データ品質チェック（quality）
  - 欠損・スパイク（急騰・急落）・重複・日付不整合の検出
  - QualityIssue オブジェクトのリストを返し、呼び出し側で影響度に応じた処理が可能
- 環境設定管理（config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェックと Settings ラッパー
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD

要求環境
-------
- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
（プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

セットアップ
--------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb
   - 開発中は editable install: pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

例: .env（簡易）
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（基本例）
-------------

1) DuckDB スキーマ初期化
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # これで required なテーブル・インデックスが作成されます

2) J-Quants から日次株価を取り込み、DuckDB に保存
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   # conn は init_schema() が返す DuckDB 接続

   # 銘柄単位または全件で取得可能
   records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
   n = save_daily_quotes(conn, records)
   print(f"{n} 件を保存しました")

   - fetch_* 系はページネーション、自動トークンリフレッシュ、リトライ、レート制御に対応しています。
   - save_* 系は ON CONFLICT DO UPDATE により冪等的にデータを格納します。

3) 監査ログスキーマの初期化（既存 DuckDB に追加）
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

   もしくは専用 DB を作る:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")

4) データ品質チェックの実行
   from kabusys.data.quality import run_all_checks

   issues = run_all_checks(conn, target_date=None)
   for issue in issues:
       print(issue.check_name, issue.table, issue.severity)
       for row in issue.rows:
           print(" ", row)

API・モジュール概要
-----------------
- kabusys.config
  - Settings クラス（settings インスタンス経由で利用）
  - .env の自動読込（ルート検出）、必須 env チェック（_require）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読込無効化

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

  設計ノート: レート制御、リトライ、401 自動リフレッシュ、fetched_at の記録、DuckDB への冪等保存などを実装。

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection（スキーマ初期化は行わない）

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- kabusys.data.quality
  - QualityIssue dataclass
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, ...)

ディレクトリ構成
--------------
src/kabusys/
- __init__.py
- config.py
- execution/
  - __init__.py
- strategy/
  - __init__.py
- monitoring/
  - __init__.py
- data/
  - __init__.py
  - jquants_client.py
  - schema.py
  - audit.py
  - quality.py

注意事項・運用メモ
----------------
- Python バージョン: ソース内での型表記や | ユニオンを使っているため Python 3.10 以上を推奨します。
- J-Quants API のレート制限（120 req/min）と API 利用規約を遵守してください。
- DuckDB のファイルパス（デフォルト data/kabusys.duckdb）の親ディレクトリは自動作成されます。
- .env の自動読込はプロジェクトルート（.git または pyproject.toml）を基準に行われます。配布パッケージ化後でも動作するように設計されていますが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用することで自動ロードを無効化できます。
- save_* 関数は基本的に冪等（ON CONFLICT DO UPDATE）なので、繰り返し実行してもデータの重複は防げますが、外部からの直接挿入やスキーマ変更により重複が発生する可能性があるため quality.check_duplicates を定期実行することを推奨します。

貢献・拡張
--------
- strategy/、execution/、monitoring/ ディレクトリはフレームワーク用の拡張ポイントです。戦略ロジック、発注実行、監視アラートなどを実装・統合してください。
- J-Quants クライアントは必要に応じて取得項目を増やし、保存用のマッピングロジックを拡張できます。

ライセンス
--------
（このリポジトリにライセンスファイルがあればそれに従ってください。README に明示されていない場合はリポジトリの所有者に確認してください。）

----- 
README は以上です。必要であればセットアップスクリプト例、単体テストの実行方法、あるいは CI 設定例（GitHub Actions）などの追記を作成します。どの項目を優先して追加しますか？