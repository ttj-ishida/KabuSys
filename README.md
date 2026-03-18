# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API や RSS フィードからのデータ取得、DuckDB を使ったスキーマ管理、ETL パイプライン、品質チェック、監査ログ用スキーマなどを提供します。

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務データ・マーケットカレンダーを安全に取得して永続化する
- RSS フィードからニュースを収集し、記事と銘柄コードの紐付けを行う
- DuckDB 上にデータスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化する
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマを提供する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する

設計上の注意点：
- API レート制限やリトライ、トークン自動更新、Look-ahead バイアス対策（fetched_at の記録）、冪等的保存（ON CONFLICT）などが組み込まれています。
- ニュース収集では SSRF 対策、XML 脆弱性対策、受信サイズ制限など安全性に配慮しています。

---

## 機能一覧

- 設定管理
  - 環境変数および .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で必要な設定値を取得

- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応、レート制御、リトライ、トークンリフレッシュ）
  - 財務指標（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・記事ID生成（URL正規化→SHA-256）
  - raw_news へのバルク保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け（news_symbols）
  - SSRF・XML 攻撃対策、受信サイズ制限、gzip 対応

- スキーマ管理（kabusys.data.schema）
  - DuckDB の完全なスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path)／get_connection(db_path)

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー・株価・財務の差分取得、保存、品質チェックを実行
  - 差分取得ロジック、backfill、品質チェック呼び出しを備える

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job() による夜間差分更新

- 品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks() でまとめて実行し QualityIssue を取得

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査テーブルの初期化（init_audit_schema / init_audit_db）
  - UTC タイムゾーン固定、冪等キー（order_request_id）を利用した追跡性確保

- その他
  - strategy / execution / monitoring モジュール用のパッケージ構造（拡張ポイント）

---

## 必要条件 / 依存パッケージ

（プロジェクトの pyproject.toml / requirements.txt を参照してください。ここでは主要な依存例を示します）

- Python 3.9+
- duckdb
- defusedxml

例（最低限）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境を作成して有効化（推奨）
- macOS / Linux:
  python -m venv .venv
  source .venv/bin/activate

- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
  pip install -r requirements.txt
（requirements.txt がなければ最低限 duckdb と defusedxml をインストールしてください）
  pip install duckdb defusedxml

4. 環境変数の設定
- プロジェクトルートに .env ファイルを置くと自動で読み込まれます（.env.local は上書き優先）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（settings から参照されるもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live; default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL; default: INFO)

例 .env:
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

5. データベース初期化（DuckDB スキーマ）
Python REPL やスクリプトで:
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

監査ログ専用 DB:
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要ユースケース）

以下は代表的な呼び出し方法の例です。

- settings の利用（環境変数取得）
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live

- DuckDB スキーマ初期化
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

- J-Quants から株価を取得して保存
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)

- 日次 ETL（推奨の高レベル API）
from datetime import date
from kabusys.data import pipeline, schema
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュース収集ジョブ
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# 既知銘柄コードセットを渡して紐付けを行うことが可能
known_codes = {"7203", "6758", "9432"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)

- カレンダー判定ユーティリティ
from kabusys.data import calendar_management as cm
conn = schema.get_connection("data/kabusys.duckdb")
d = date(2024, 3, 1)
cm.is_trading_day(conn, d)
cm.next_trading_day(conn, d)

- 品質チェック
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)

- 監査スキーマ初期化（audit）
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=False)
# または audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 注意点 / 実装上の注記

- 自動環境変数読み込み:
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探し、.env と .env.local を読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途に便利）。
  - .env.local は .env の値を上書き（OS 環境変数は保護され上書きされません）。

- J-Quants クライアント:
  - API レート制御（120 req/min）を内部で行います。
  - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュを実装しています。
  - ページネーション対応で pagination_key を使って全ページを取得します。
  - 保存は冪等で、ON CONFLICT による上書きや排除を行います。

- ニュース収集:
  - URL 正規化、トラッキングパラメータ除去、記事ID の SHA-256 によるハッシュ化（先頭32文字）で冪等性確保。
  - defusedxml を利用して XML 関連の脆弱性を回避。
  - SSRF 対策としてスキーム検証・リダイレクト検査・プライベートアドレス検査を行います。
  - レスポンスサイズは上限（10MB）で制限し、gzip 解凍後もチェックします。

- スキーマ:
  - Raw → Processed → Feature → Execution までのテーブルを定義しています。
  - 監査ログ用スキーマは別途 init_audit_schema で追加できます。
  - 多くのクエリパターンに対してインデックスを作成します。

- 品質チェック:
  - Fail-Fast ではなくすべてのチェックを走らせて問題一覧を返します。呼び出し側で重大度（error/warning）に応じて対処してください。

---

## ディレクトリ構成

プロジェクト（src/kabusys）の主要ファイルとモジュール:

- src/kabusys/
  - __init__.py  (version: 0.1.0)
  - config.py    (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py      (J-Quants API クライアント: fetch/save)
    - news_collector.py      (RSS ニュース収集・保存・銘柄抽出)
    - schema.py              (DuckDB スキーマ定義・init)
    - pipeline.py            (ETL パイプライン / run_daily_etl)
    - calendar_management.py (マーケットカレンダー管理・判定)
    - audit.py               (監査ログスキーマ初期化)
    - quality.py             (データ品質チェック)
  - strategy/
    - __init__.py
    (戦略ロジック用の拡張ポイント)
  - execution/
    - __init__.py
    (発注 / ブローカー連携用の拡張ポイント)
  - monitoring/
    - __init__.py
    (監視・メトリクス用の拡張ポイント)

---

## 開発 / テストメモ

- テスト実行時に自動 .env 読み込みを無効化したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- DB の初期化には in-memory モードを利用可能:
  conn = schema.init_schema(":memory:")

- モジュール内部のネットワーク呼び出し（例: news_collector._urlopen）はテストでモックしやすいように設計されています。

---

## ライセンス & 貢献

この README では省略します。リポジトリの LICENSE ファイルを参照してください。バグ報告・改善提案・プルリクエストは歓迎します。

---

以上が KabuSys の概要と使い方のサマリです。追加の利用シナリオ（取引実行フロー、Slack 通知連携、スケジューリング例など）や具体的なコードスニペットが必要であればお知らせください。