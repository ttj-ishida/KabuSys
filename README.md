# KabuSys

日本株の自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS 等から市場データを収集し、DuckDB に保存・整形し、品質チェックや監査ログ（発注→約定のトレーサビリティ）を提供します。

---

## 概要

KabuSys は日本株向けのデータ収集・ETL・品質管理・監査基盤を提供する Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存
- RSS フィードからニュースを安全に収集し、株式コードと紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）
- ETL パイプライン（差分更新・バックフィル・カレンダー先読み・品質チェック）

設計上の特徴（抜粋）：
- J-Quants API のレート制限（120 req/min）厳守（内部でスロットリング）
- リトライ、トークン自動リフレッシュ（401 時）を備えた堅牢なクライアント実装
- NewsCollector は SSRF / XML bomb / 大容量レスポンスなどの安全対策を実装
- DuckDB への保存は冪等性（ON CONFLICT）を考慮

---

## 主な機能一覧

- data.jquants_client
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制御、リトライ、id_token 自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes 等）

- data.news_collector
  - RSS フィードの取得・前処理・記事ID生成（URL 正規化→SHA-256）・保存
  - SSRF 対策、gzip 解凍上限、XML パースの安全化（defusedxml）
  - 銘柄コード抽出と news_symbols への紐付け

- data.schema / data.audit
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(), init_audit_db() による初期化

- data.pipeline
  - 日次 ETL 実行（run_daily_etl）
  - 差分取得、バックフィル、品質チェックの一括管理

- data.calendar_management
  - market_calendar に基づく営業日判定・前後営業日取得・カレンダー更新ジョブ

- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）

- config
  - .env / 環境変数の読み込み、自動ロード（プロジェクトルート基準）
  - 必須設定値取得用 Settings (settings.jquants_refresh_token 等)
  - 自動ロードの無効化やロード優先順位制御をサポート

---

## セットアップ

前提:
- Python 3.9+（typing に | を使うため最低限のバージョンを確認してください）
- duckdb, defusedxml などが必要

推奨インストール例（プロジェクトルートで）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

（プロジェクトが requirements.txt を提供している場合はそれを使用してください）

環境変数（必須/任意）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env と .env.local を自動読み込みします。
  - 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env:
    JQUANTS_REFRESH_TOKEN="xxxxx"
    KABU_API_PASSWORD="your_password"
    SLACK_BOT_TOKEN="xoxb-..."
    SLACK_CHANNEL_ID="C01234567"
    DUCKDB_PATH="data/kabusys.duckdb"
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

---

## 使い方（基本例）

以下はライブラリを使った典型的なワークフロー例です。

1) DuckDB スキーマ初期化

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ":memory:" を指定するとインメモリ DB になります

2) 監査ログ用 DB 初期化（別ファイルで管理する場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

3) 日次 ETL を実行（J-Quants トークンは settings 経由で取得）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())

- run_daily_etl は市場カレンダー（先読み）、株価、財務の差分取得と保存、品質チェックを順に実行します。
- バックフィル日数や spike 閾値などは引数で調整可能です。

4) 単独ジョブの実行例

- 株価差分 ETL:
from kabusys.data.pipeline import run_prices_etl
from datetime import date
fetched, saved = run_prices_etl(conn, target_date=date.today())

- ニュース収集:
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄コードを用意
results = run_news_collection(conn, known_codes=known_codes)
print(results)

- 品質チェック:
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

- カレンダー更新ジョブ:
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)

5) J-Quants クライアント直接呼び出し（テスト用など）
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点:
- get_id_token は id_token を発行するための POST を行います。_request() は 401 を受けた際に自動リフレッシュを行う実装があります。
- ニュース取得は外部 URL をフェッチするためネットワーク権限やタイムアウトに注意してください（デフォルトタイムアウト 30 秒）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・Settings 管理、.env 自動ロード
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存関数・レート制御・リトライ）
  - news_collector.py
    - RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - calendar_management.py
    - market_calendar の管理・営業日判定・更新ジョブ
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）初期化
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付不整合）
- strategy/
  - __init__.py (戦略関連モジュールを配置)
- execution/
  - __init__.py (発注実装・ブローカー連携を配置)
- monitoring/
  - __init__.py (監視・アラート関連を配置)

README に記載の無い詳細（戦略・発注インターフェース等）は個別モジュールとして実装する想定です。

---

## 実装上の注意・設計コメント（要約）

- J-Quants クライアントは 120 req/min のレート制限に対応（固定間隔スロットリング）。
- HTTP の一時エラー（408/429/5xx）に対して指数バックオフで最大リトライを行う。
- 401 を受けた場合はリフレッシュトークンから id_token を再取得して 1 回だけリトライする。
- ニュース収集は SSRF、XML Bomb、gzip 膨張対策、トラッキングパラメータ除去、記事 ID の冪等生成を実装。
- DuckDB 側は INSERT ... ON CONFLICT を活用して冪等性を実現。
- audit スキーマは監査目的で厳格な外部キーと UTC タイムスタンプを使用。

---

## テスト・開発時のヒント

- .env の自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからインポートしてください（テストで環境を制御したい場合に便利）。

- DB を破壊せずに高速に試したい場合:
  - init_schema(":memory:") でインメモリ DuckDB を利用できます。

---

必要に応じて、こちらの README をプロジェクトの実際の要件（Python バージョン、依存パッケージ一覧、実行スクリプト、CI 設定など）に合わせて調整します。追加で載せたいサンプルやコマンド （例: systemd / cron / Airflow でのスケジュール例、Slack 通知フロー 等）があれば教えてください。