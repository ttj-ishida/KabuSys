KabuSys
=======

概要
----
KabuSys は日本株のデータ取得・ETL・品質チェック・監査ログ・発注フローを想定した自動売買プラットフォームのコアライブラリです。  
主に以下を提供します：

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得クライアント
- DuckDB ベースのスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ

設計上のポイント：
- J-Quants API のレートリミット（120 req/min）に従う固定間隔スロットリング
- リトライ（指数バックオフ、401 時の自動トークンリフレッシュ対応）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 監査ログは削除せずトレーサビリティを保証（UTC タイムスタンプ）

主な機能
--------
- データ取得
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - get_id_token（リフレッシュトークンからの ID トークン発行）
- ETL（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分取得、バックフィル考慮）
  - 市場カレンダー先読み
  - 品質チェック（quality モジュール）
  - run_daily_etl による一括実行（エラーはステップ毎にハンドリング）
- データベース
  - DuckDB スキーマ初期化：init_schema()
  - 監査ログの初期化：init_audit_schema() / init_audit_db()
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境設定管理（.env 自動ロード、必須値チェック）

動作要件
--------
- Python 3.10+
- duckdb（Python パッケージ）
- （J-Quants / kabuステーション / Slack 連携を使う場合はそれぞれの API アクセス情報）

セットアップ手順
----------------

1. 仮想環境作成（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 最低限 duckdb が必要です。プロジェクト全体をローカルで使う場合はソースをパスに通すかパッケージ化してください。
     - pip install duckdb
   - 開発時はプロジェクトルート（pyproject.toml がある想定）で:
     - pip install -e .

   もしパッケージ化されていない場合は PYTHONPATH を通して実行できます：
     - export PYTHONPATH=$(pwd)/src:$PYTHONPATH
     - （Windows は適切に設定してください）

3. 環境変数（.env）を設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（後述の「環境変数」参照）を設定してください。

環境変数（.env の例）
---------------------
以下は .env の例（.env.example 相当）：

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 任意
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development    # development | paper_trading | live
LOG_LEVEL=INFO

必須項目:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

KABUSYS の設定は kabusys.config.Settings から型安全に取得できます。

初期化（DuckDB スキーマ）
------------------------
DuckDB データベースを初期化して全テーブルを作成します。:memory: を指定するとインメモリ DB を使用できます。

例:

from pathlib import Path
from kabusys.data import schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)  # テーブル群を作成して接続を返す

監査ログ（audit）を既存の接続に追加する場合:

from kabusys.data import audit
audit.init_audit_schema(conn)

ETL（日次処理）の実行例
----------------------
run_daily_etl を使って日次 ETL（カレンダー取得／株価差分取得／財務差分取得／品質チェック）を実行できます。

例:

from datetime import date
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())

主なオプション:
- id_token: J-Quants のアクセストークンを外部から注入可能（テスト用）。
- run_quality_checks: 品質チェックを有効/無効。
- spike_threshold: スパイク判定閾値（デフォルト 0.5 = 50%）。
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）。
- calendar_lookahead_days: カレンダーの先読み日数（デフォルト 90 日）。

J-Quants クライアントについて
------------------------------
- 関数: get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
- 特徴:
  - API レート制御（_RateLimiter による 120 req/min のスロットリング）
  - リトライ（408/429/5xx、指数バックオフ、最大 3 回）
  - 401 を受けた場合は自動でリフレッシュトークンから再取得して再試行（1 回）
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - 保存は冪等（ON CONFLICT DO UPDATE）

保存関数:
- save_daily_quotes(conn, records)
- save_financial_statements(conn, records)
- save_market_calendar(conn, records)

品質チェック（quality）
-----------------------
提供チェック:
- 欠損 (check_missing_data)
- スパイク (check_spike)
- 重複 (check_duplicates)
- 日付整合性 (check_date_consistency)
- run_all_checks で一括実行し、QualityIssue オブジェクトのリストを返す（severity: error|warning）

監査ログ（audit）
-----------------
監査用スキーマは signal_events / order_requests / executions を提供し、トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を維持します。init_audit_schema により既存の DuckDB 接続へ追加できます。実運用想定で全て UTC タイムスタンプを使います。

開発時のヒント
--------------
- 自動で .env を読み込みます。テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings から設定値を取得してください（必須の欠如は ValueError を投げます）。
- id_token をテストで直接注入するとネットワークリトライやトークン自動更新の影響を切り分けられます。

ディレクトリ構成
----------------
プロジェクトの主要ファイル・ディレクトリ（抜粋）:

src/kabusys/
- __init__.py                     : パッケージ定義（__version__）
- config.py                       : 環境変数・設定管理（Settings）
- data/
  - __init__.py
  - jquants_client.py             : J-Quants API クライアント（取得・保存）
  - schema.py                     : DuckDB スキーマ定義・init_schema/get_connection
  - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
  - audit.py                      : 監査ログスキーマ初期化
  - quality.py                    : データ品質チェック
- strategy/
  - __init__.py                    : 戦略レイヤー（拡張用）
- execution/
  - __init__.py                    : 発注・約定レイヤー（拡張用）
- monitoring/
  - __init__.py                    : 監視関連（拡張用）

利用上の注意
------------
- 実際の発注・約定機能（証券会社連携、kabuステーションなど）や Slack 通知はこのコアライブラリ単体では完結しません。必要なブリッジ（execution レイヤー、monitoring/通知）を実装してください。
- 本ライブラリはローカル/バックテスト/ペーパートレード/本番を想定して環境（KABUSYS_ENV）で振る舞いを切り替えるため、KABUSYS_ENV を適切に設定してください（development, paper_trading, live）。
- DuckDB のファイル位置は DUCKDB_PATH で指定できます（デフォルト data/kabusys.duckdb）。

ライセンス / 貢献
----------------
（この README にはライセンス表記が含まれていません。配布時には適切な LICENSE ファイルを追加してください。）

問い合わせ / 追加実装
--------------------
- strategy、execution、monitoring フォルダは拡張用のエントリポイントです。アルゴリズム実装、ブローカー接続、アラート/監視機能はそれらのモジュールに実装してください。必要があれば README を拡張し具体的な実装例を追加できます。