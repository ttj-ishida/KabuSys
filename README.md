KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買基盤（データプラットフォーム + ETL + 監査ログ）です。  
J-Quants API から株価・財務・マーケットカレンダーを取得し、DuckDB に保存・整形して戦略や発注層で利用できる形に整えます。ニュース収集（RSS）、データ品質チェック、監査ログ（シグナル→発注→約定のトレース）などの機能を備えています。

主な特徴
--------
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日からの差分を自動算出）
  - バックフィル取り込み（後出し修正に対応）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、記事ID の SHA-256 ベース生成
  - SSRF 対策、サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義一式
  - 監査ログ（signal_events / order_requests / executions）用の専用初期化
- データ品質モジュール
  - 欠損データ、スパイク、重複、日付不整合を検出し QualityIssue を返す

セットアップ
-----------
前提
- Python 3.10 以上（型ヒントに | 演算子を使用）
- Git

1. リポジトリをクローン
   - git clone ... (この README はリポジトリルートに置いてください)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（本コードベースで使用している主要ライブラリ）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください: pip install -r requirements.txt）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO (デフォルト)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化
     - DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH=data/monitoring.db (デフォルト)

   例 (.env.example)
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

データベース初期化
-----------------
DuckDB スキーマを作成するには data.schema.init_schema を使用します。

簡単な例:
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

監査ログテーブルのみ追加する場合:
from kabusys.data import audit
# 既に init_schema で取得した conn を渡す
audit.init_audit_schema(conn)

使い方（主要 API）
-----------------

1) ETL（日次）
from datetime import date
from kabusys.data import schema, pipeline
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# 当日分を処理（デフォルトで品質チェック実行）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

run_daily_etl は以下を実行します:
- 市場カレンダー ETL（先読み）
- 株価差分 ETL（バックフィル対応）
- 財務データ差分 ETL
- 品質チェック（オプションで無効化可）

2) J-Quants クライアント（個別取得）
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = jq.get_id_token()  # settings.jquants_refresh_token を利用して id token を取得
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存
from kabusys.data import schema
conn = schema.get_connection(settings.duckdb_path)
jq.save_daily_quotes(conn, records)

3) ニュース収集
from kabusys.data import news_collector
from kabusys.data import schema
conn = schema.get_connection(settings.duckdb_path)
# sources を省略すると内部定義の DEFAULT_RSS_SOURCES を使用
results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(results)

4) 品質チェックを単体で実行
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

設定の自動読み込み
------------------
kabusys.config モジュールは次の順で環境変数を自動ロードします（プロジェクトルートが特定できる場合）:
OS 環境変数 > .env.local > .env

自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで有用）。

主な環境変数一覧
----------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development|paper_trading|live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

ディレクトリ構成
----------------
リポジトリの主要ファイル構成（要約）:

src/kabusys/
- __init__.py
- config.py                # 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント + 保存ロジック
  - news_collector.py      # RSS ニュース収集・保存
  - schema.py              # DuckDB スキーマ定義と初期化
  - pipeline.py            # ETL パイプライン（差分更新・日次 ETL）
  - audit.py               # 監査ログ（signal/events/order_requests/executions）
  - quality.py             # データ品質チェック
- strategy/
  - __init__.py            # 戦略層（拡張ポイント）
- execution/
  - __init__.py            # 発注・執行インターフェース（拡張ポイント）
- monitoring/
  - __init__.py            # 監視用モジュール（拡張ポイント）

開発メモ / 設計の意図（抜粋）
---------------------------
- 冪等性: DB への挿入は ON CONFLICT を使用して冪等に行うことで再実行可能な ETL を実現。
- トレーサビリティ: signal→order_request→executions の階層で UUID を連鎖させ、監査ログによりフローを完全に追跡可能にする。
- セキュリティ: RSS 処理で SSRF 対策や defusedxml を使用、レスポンスサイズ制限を設けて DoS を軽減。
- 可観測性: 取得時刻（UTC）、fetched_at、created_at を保存してデータの「知得タイミング」をトレース可能に。

よくある質問
------------
Q. テスト用に .env を読み込ませたくない/差し替えたい  
A. KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。テスト中は settings をモックするか環境を明示的に設定してください。

Q. DuckDB の初期化を忘れた場合どうなる？  
A. schema.get_connection はスキーマを作成しません。初回は schema.init_schema を使ってテーブル作成を行ってください。

追加事項 / 今後の拡張
-------------------
- strategy / execution / monitoring パッケージは拡張ポイントとして用意されています。実際の戦略ロジックやブローカー連携はここに実装してください。
- Slack 通知や運用用 CLI、ジョブスケジューラ（cron / Airflow / Prefect）との連携はプロジェクト側で追加可能です。

--------------------------------------------------
この README はコードベースのソースコメントに基づいて作成されています。実運用前に API キー・パスワード等の管理、実際のブローカー接続における安全性（資金管理・二重発注防止・テストネットでの検証）を十分に行ってください。