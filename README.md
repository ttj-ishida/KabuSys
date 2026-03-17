KabuSys — 日本株自動売買プラットフォーム（README 日本語）

概要
----
KabuSys は日本株向けのデータ収集・ETL・品質チェック・監査ログ・（将来的な）戦略・発注実行を想定したライブラリ群です。本コードベースは以下の主要機能を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、JPXカレンダー）
- DuckDB を用いたスキーマ定義・初期化・永続化
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS を用いたニュース収集（正規化・SSRF対策・トラッキング除去）
- 市場カレンダー管理（営業日判定・next/prev/trading days）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）
- 設定管理（.env / 環境変数の自動読み込み／保護）

主な機能一覧
--------------
- config
  - .env / 環境変数読み込み、必須値チェック、環境（development/paper_trading/live）やログレベル判定
- data.jquants_client
  - J-Quants との通信（レート制御、リトライ、トークン自動リフレッシュ、ページネーション）
  - fetch/save 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_*）
- data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit 用のテーブル）
  - init_schema / get_connection
- data.pipeline
  - 日次 ETL（run_daily_etl）、差分更新ロジック、品質チェック実行
- data.news_collector
  - RSS 収集（XML の安全パース、SSRF 対策、URL 正規化、記事ID生成、DuckDB への冪等保存）
- data.calendar_management
  - market_calendar の更新ジョブ、営業日判定ロジック（is_trading_day / next_trading_day 等）
- data.quality
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue で結果を返す）
- data.audit
  - 監査用テーブル群（signal_events / order_requests / executions）と初期化ユーティリティ
- strategy / execution / monitoring
  - 将来的な戦略、発注、監視モジュール用の名前空間（今はパッケージプレースホルダ）

セットアップ手順
----------------
前提
- Python 3.10 以上（ソース内で | 型ヒント等を使用）
- 基本的には pip により依存パッケージを導入します。

推奨インストール手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクト配布に requirements.txt があれば pip install -r requirements.txt を使用してください）

3. 開発インストール（ソースツリー直下で）
   - pip install -e .

環境変数 (.env)
- プロジェクトルートに .env / .env.local を置くことで自動で読み込まれます（CWD ではなくパッケージファイル位置から .git / pyproject.toml をさかのぼってプロジェクトルートを探索）。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

オプション（デフォルトあり）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

使い方（簡単なコード例）
-----------------------

1) DuckDB スキーマの初期化
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# :memory: を渡すとインメモリ DB

2) 監査ログ専用スキーマ初期化（既存接続に追加）
from kabusys.data import audit
audit.init_audit_schema(conn)  # 既存 conn に作成（トランザクションオプションあり）
# またはファイル単体で初期化:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

3) 日次 ETL の実行
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
# ETLResult の詳細は result.to_dict() で辞書化できます

4) ニュース収集ジョブ（RSS）
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
counts = run_news_collection(conn, known_codes=known_codes)
print("news collected:", counts)

5) J-Quants からの直接データ取得（テスト等）
from kabusys.data import jquants_client as jq
# id_token を自動的に取得してページネーション対応で取得
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 取得データは save_* 関数で DuckDB に保存可能
jq.save_daily_quotes(conn, quotes)

6) データ品質チェック（単体実行）
from kabusys.data import quality
issues = quality.run_all_checks(conn, reference_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)

設定と運用上の注意
-----------------
- レート制限: J-Quants は 120 req/min を想定。jquants_client 内で固定間隔レートリミッタを備えています。
- 冪等性: save_* 関数は ON CONFLICT DO UPDATE / DO NOTHING を利用しているため、ETL を再実行しても重複を避けられます。
- トークン自動リフレッシュ: 401 を受け取ると一度だけリフレッシュを試行します。
- Look-ahead 対策: データを保存する際に fetched_at を記録し、「いつデータを取得したか」を追跡できます。
- RSS 収集: SSRF 対策・gzip/Bomb 対応・トラッキングパラメータ除去などの保護機構があります。
- テスト: 自動 env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すると環境に依存しない単体テストが容易です。

ディレクトリ構成
----------------
（省略可能ファイルを除く、主要モジュールのみ示します）

- src/kabusys/
  - __init__.py             - パッケージ初期化、__version__
  - config.py               - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     - J-Quants API クライアント（fetch/save）
    - news_collector.py     - RSS ニュース収集・保存ロジック
    - pipeline.py           - ETL パイプライン（run_daily_etl 等）
    - schema.py             - DuckDB スキーマ定義 / 初期化
    - calendar_management.py- 市場カレンダー更新・営業日判定
    - audit.py              - 監査ログスキーマと初期化
    - quality.py            - データ品質チェック
  - strategy/
    - __init__.py           - 戦略用名前空間（将来拡張）
  - execution/
    - __init__.py           - 発注/実行レイヤー名前空間（将来拡張）
  - monitoring/
    - __init__.py           - 監視モジュールプレースホルダ

補足（開発者向け）
-----------------
- ログレベルは環境変数 LOG_LEVEL で制御します。
- KABUSYS_ENV により is_live/is_paper/is_dev のフラグが設定されます。発注/実行ロジックを実装する際はこのフラグで安全に挙動を分岐してください。
- データベース初期化は init_schema() を一度実行してから ETL を回す運用が想定されています。
- DuckDB を用いるため軽量にローカル保存が可能です。大規模運用時は DB ファイルのバックアップや検証を検討してください。

ライセンス / コントリビューション
---------------------------------
（このリポジトリに合わせて追記してください）

以上。必要であれば README にサンプル .env.example、requirements.txt の例、より具体的な CLI/サービス化（systemd / cron / Airflow）などの運用例も追記できます。どの情報を追加したいか教えてください。