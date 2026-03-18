# KabuSys

日本株自動売買のためのデータ基盤・ETL・監査ライブラリ群です。J-Quants API や RSS ニュースを収集し、DuckDB に冪等に保存、品質チェックや戦略／発注層と連携するための基盤機能を提供します。

バージョン: 0.1.0

---

## 主な概要

- J-Quants API から株価（日足）・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して記事・銘柄紐付けを DuckDB に保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）を提供
- マーケットカレンダー管理（営業日判定、前後営業日の算出、夜間更新ジョブ）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマと初期化
- 設定は環境変数／.env で管理。プロジェクトルートの .env/.env.local を自動読み込み

設計上の特徴:
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 の自動リフレッシュ）
- DuckDB への保存は冪等（ON CONFLICT ...）で重複や再実行に耐える
- RSS 収集時の SSRF/Gzip Bomb 等の安全対策、XML パースに defusedxml を採用

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）
  - レートリミット・リトライ・token キャッシュ実装
- data.news_collector
  - RSS の取得（gzip 対応、SSRF/ホスト検査、レスポンスサイズ制限）
  - 記事正規化（URL 正規化、トラッキングパラメータ除去）
  - raw_news 保存（INSERT ... RETURNING）、news_symbols 紐付け
- data.schema
  - DuckDB のスキーマ定義と init_schema / get_connection
  - Raw / Processed / Feature / Execution / Audit 系テーブル定義
- data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL の統合エントリポイント run_daily_etl（品質チェック含む）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間更新ジョブ）
- data.audit
  - 監査ログ用テーブル初期化（init_audit_schema / init_audit_db）
- data.quality
  - 欠損・重複・スパイク・日付不整合の品質チェック（run_all_checks）
- config
  - 環境変数読み込み（.env 自動読み込み）、Settings クラス（settings オブジェクト）

---

## 要件

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime, hashlib, gzip 等

インストールはプロジェクトに合わせて requirement を整備してください。テストや開発時は次のようにインストールする例が考えられます:

pip install duckdb defusedxml

（実際の配布パッケージでは setup/pyproject に依存関係を記載してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動で読み込まれます（.git または pyproject.toml を探索してプロジェクトルートを特定）
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

.env に設定する主なキー（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

その他（任意、デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

以下はライブラリの主要な使い方の抜粋例です。

- DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・保存・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 省略時は本日を対象、設定は settings 経由
print(result.to_dict())
```

- ニュース収集ジョブ実行
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出のための有効銘柄コード集合（例: set of "7203", "6758" ...）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

- カレンダー夜間更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- 監査スキーマ初期化（監査専用 DB を別に作る場合）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定値取得
```
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

---

## 重要な実装上のポイント

- 環境変数自動読み込み
  - config モジュールはパッケージインポート時にプロジェクトルートを探索（.git または pyproject.toml）して `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数で既に設定されているキーは `.env` による上書きを保護します（`.env.local` は上書き可能）。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト時に便利です）。

- J-Quants API クライアント
  - リクエストは 120 req/min までに制御（固定間隔のスロットリング）
  - リトライ: 最大 3 回（408/429/5xx を対象）、指数バックオフ、429 の場合は Retry-After を優先
  - 401 を受け取った場合はリフレッシュトークンから id_token を再取得して 1 回だけリトライ
  - 取得時刻（fetched_at）を UTC で保管し、Look-ahead Bias を防止

- RSS / News Collector
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256（先頭32文字）で記事IDを生成して冪等性を担保
  - SSRF 対策: リダイレクト先の検査、ホストがプライベートアドレスの場合は拒否
  - レスポンスサイズ上限（デフォルト 10MB）でメモリ DoS を防止
  - 保存はチャンク化して一括 INSERT、INSERT ... RETURNING で挿入された ID を取得

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit の各レイヤーを定義
  - 多くのテーブルで PRIMARY KEY / CHECK 制約を設け、冪等性・整合性を重視
  - インデックスを追加して頻出クエリを高速化

- 品質チェック
  - 欠損、重複、スパイク、日付不整合を検出するチェック群（fail-fast ではなく問題を集約して返す）
  - run_all_checks でまとめて実行し、結果は QualityIssue オブジェクトのリストで返る

---

## 開発・テストノート

- テスト時のフック:
  - news_collector._urlopen 等をモックして HTTP レスポンスを差し替え可能
  - config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できる
  - jquants_client 内の id_token キャッシュはモジュールレベルのキャッシュで管理されているため、テスト時は _get_cached_token(force_refresh=True) 等で制御可能

- トランザクション:
  - news_collector の raw_news / news_symbols 保存や audit.init_audit_schema の transactional オプションはトランザクション制御に注意（DuckDB のトランザクション挙動に依存）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - audit.py
  - quality.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

主なファイル説明:
- config.py: 環境変数読み込みと Settings 定義
- data/schema.py: DuckDB スキーマ定義と init_schema/get_connection
- data/jquants_client.py: J-Quants API クライアント（取得 + 保存）
- data/news_collector.py: RSS 収集・正規化・保存ロジック
- data/pipeline.py: ETL パイプライン（差分取得、品質チェック）
- data/calendar_management.py: マーケットカレンダー管理 & ユーティリティ
- data/audit.py: 監査ログ（order/signals/executions）用 DDL と初期化
- data/quality.py: データ品質チェック

---

## ライセンス & 貢献

（本テンプレートでは明示していません。実際のプロジェクトでは LICENSE を明記してください。）

貢献する場合は、Issue / Pull Request を通してバグ報告や機能提案をお願いします。テストとドキュメント付きの PR を歓迎します。

---

README は最小限の導入と開発者向け情報をまとめたものです。より詳細な設計（DataPlatform.md 等）や運用手順は別途ドキュメントにまとめて管理してください。