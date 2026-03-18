# KabuSys

日本株向け自動売買 / データ基盤ライブラリ KabuSys の README（日本語）

概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・品質チェック・特徴量生成・監査ログ管理・ニュース収集・研究用ユーティリティを備えた内部ライブラリ群です。主に以下を目的とします。

- J-Quants API からの時系列データ・財務データ・市場カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義・初期化・永続化（冪等保存）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と銘柄抽出、冪等保存
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC・統計サマリー
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化

設計上、production の発注 API 等には影響を与えない「データ・研究」コード群と、発注・実行に関するスキーマ設計（監査テーブル）を含みます。

---

## 主な機能一覧

- 環境変数読み込み・設定管理（.env/.env.local を自動ロード、無効化フラグあり）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限（120 req/min）、リトライ、ID トークン自動リフレッシュ
  - DuckDB への冪等保存 save_* 系関数
- DuckDB スキーマ管理
  - init_schema(db_path) によるテーブル・インデックス作成（Raw / Processed / Feature / Execution 層）
  - 監査ログ用 init_audit_schema / init_audit_db
- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分取得ロジック、バックフィル、品質チェック統合
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（run_all_checks）
- ニュース収集
  - RSS 取得（SSRF対策、gzip制限、XMLセーフパーサ）・正規化・ID生成・DB保存（冪等）
  - 銘柄コード抽出（4桁数字）
- 研究用ユーティリティ
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- 監査ログ設計（signal_events / order_requests / executions 等）と初期化ヘルパ

---

## 必要な環境変数

config.Settings で参照される主要な環境変数（必須は明示します）:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション等を使う場合の API パスワード
- SLACK_BOT_TOKEN: Slack 通知に使うボットトークン
- SLACK_CHANNEL_ID: Slack のチャンネルID

任意（デフォルトあり）
- KABUSYS_ENV: environment。development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると無効化可能）。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（開発用）

1. Python 環境を作成（推奨: venv / pyenv）
   python -m venv .venv
   source .venv/bin/activate

2. 依存ライブラリをインストール
   本コードベースで明示的に使用している外部依存は主に以下です:
   - duckdb
   - defusedxml

   例:
   pip install duckdb defusedxml

   （パッケージ化されている場合は pip install -e . を推奨）

3. 環境変数設定
   プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します（上記参照）。

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから初期化します（例: data/kabusys.duckdb を使用）:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査 DB を別ファイルで初期化する場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 基本的な使い方（コード例）

以下は代表的な利用例です。

1) DuckDB スキーマの初期化
```py
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行
```py
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) J-Quants から手動で株価取得（テスト / デバッグ）
```py
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
id_token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print("fetched", len(records), "saved", saved)
```

4) ニュース収集ジョブの実行
```py
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すとテキスト中の4桁コードを抽出して紐付けを行う
known_codes = {"7203","6758","9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) 研究用: モメンタムや IC 計算
```py
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target)
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6) Zスコア正規化
```py
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 主な公開 API（要点）

- config.settings: 環境設定アクセス
- data.schema.init_schema(db_path)
- data.schema.get_connection(db_path)
- data.jquants_client.get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_daily_quotes / save_financial_statements / save_market_calendar
- data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- data.news_collector.fetch_rss / save_raw_news / run_news_collection
- data.quality.run_all_checks
- data.stats.zscore_normalize
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- data.audit.init_audit_schema / init_audit_db

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）を守るためモジュール内部でスロットリングしています。複数プロセスから同時に大量リクエストする場合は注意が必要です。
- get_id_token はリフレッシュトークンを使って ID トークンを取得します。401 応答時は自動でリフレッシュし1回リトライする実装になっています。
- DuckDB テーブル作成は冪等に設計されています。既存の DB を破壊しませんが、スキーマを変更する場合の互換性は注意してください。
- NewsCollector は RSS の外部 XML 解析を行います。defusedxml を用いて XML Bomb 等を軽減していますが、運用時はソースの安全性に留意してください。
- audit.init_audit_schema は UTC タイムゾーンを設定します（SET TimeZone='UTC'）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルと役割（src/kabusys 以下）です。

- __init__.py
  - パッケージエントリ。__version__ 等。

- config.py
  - 環境変数読み込み・Settings クラス（settings オブジェクト）を提供。

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py: RSS ベースのニュース収集・前処理・DB 保存
  - schema.py: DuckDB スキーマ定義と init_schema / get_connection
  - stats.py: zscore_normalize 等統計ユーティリティ
  - pipeline.py: 日次 ETL パイプラインと差分更新ロジック
  - features.py: 特徴量ユーティリティの公開インターフェース
  - calendar_management.py: 市場カレンダー管理ヘルパ（営業日判定等）
  - audit.py: 監査ログテーブルの DDL と初期化
  - etl.py: ETLResult 再エクスポート
  - quality.py: データ品質チェック

- research/
  - __init__.py: 研究向け API の再エクスポート
  - feature_exploration.py: 将来リターン計算 / IC / summary
  - factor_research.py: momentum / volatility / value の計算

- strategy/
  - __init__.py: 戦略関連（将来的に戦略モデル等を配置）

- execution/
  - __init__.py: 発注・実行層（将来的な発注ラッパ等）

- monitoring/
  - __init__.py: 監視・メトリクス関連（空のプレースホルダ）

---

## 追加情報 / 開発

- テストや CI、requirements.txt、セットアップスクリプトは各リポジトリ方針に合わせて追加してください。
- ロギングは各モジュールで logger.getLogger(__name__) を使用しています。実運用ではハンドラ・フォーマットの設定を行ってください。
- データベースファイルのバックアップ、アクセス制御、API シークレット管理（Vault 等）を運用で検討ください。

---

もし README に追記したい利用例（例えば cron / Airflow での ETL スケジュール例、kabu API の発注フローの実例、CI テスト例など）があれば教えてください。必要に応じてサンプルスクリプトや運用ガイドを追加します。