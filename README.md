# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や RSS を利用したデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、データ品質チェック、監査ログ構造などを提供します。

主な設計方針は「冪等性」「トレーサビリティ」「外部 API のレート制御と堅牢なリトライ」「SSRF 等のセキュリティ対策」です。

---

## 機能一覧

- 環境変数管理
  - .env / .env.local から自動読み込み（自動無効化フラグあり）
  - 必須項目は取得時に検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、マーケットカレンダーの取得
  - レート制限（120 req/min）の制御
  - 再試行（指数バックオフ、最大 3 回）、401 時の自動トークン更新
  - 取得時刻（fetched_at）の記録、DuckDB への冪等保存（ON CONFLICT）

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得 → テキスト前処理 → raw_news へ冪等保存
  - URL 正規化・トラッキングパラメータ除去・記事ID は SHA-256（先頭32文字）
  - SSRF 防止、Gzip サイズ制限、XML パーサ保護（defusedxml）
  - 銘柄コード抽出、news_symbols 保存

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義
  - インデックス、外部キー、各種テーブル用 DDL を管理
  - init_schema() による初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）
  - テスト容易性のため id_token 注入可能

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
  - 夜間バッチ更新 job（calendar_update_job）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル群
  - UUID を用いたトレーサビリティ、UTC タイムゾーン固定
  - init_audit_schema / init_audit_db を提供

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

---

## 前提 / 必要環境

- Python 3.9 以上（typing | の使用を考慮）
- ライブラリ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作する部分も多いですが、実運用では上記をインストールしてください。

requirements.txt が無い場合は最低限次をインストールしてください:
pip install duckdb defusedxml

（プロジェクトで別パッケージを想定する場合は該当パッケージを追加してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （追加でテストやロギング用のパッケージを導入してください）
4. 環境変数ファイルを作成
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env に設定する代表的な環境変数（例）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: 必須値（環境変数）が不足している場合、settings.プロパティで ValueError が投げられます。

---

## 初期化（DB スキーマ）

DuckDB スキーマの初期化例:

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
# conn は duckdb.DuckDBPyConnection

監査ログ専用 DB の初期化:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

- init_schema は冪等（既存テーブルがあればスキップ）
- init_audit_schema は UTC タイムゾーンを設定します

---

## 使い方（代表的な呼び出し例）

- 日次 ETL（市場カレンダー、株価、財務、品質チェック）実行:

from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- RSS ニュース収集の実行:

from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
# 既知の銘柄コードセットを用意（extract_stock_codes に使用）
known_codes = {"7203", "6758", "9432"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}

- カレンダー夜間更新ジョブ:

from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")

- J-Quants から直接データ取得:

from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 品質チェック呼び出し:

from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)

注意点:
- jquants_client は内部でレート制御・リトライを行います。テスト時は id_token を注入してモックが可能です。
- news_collector は SSRF 対策やサイズ制限を行っており、HTTP ハンドラを差し替えることでテスト可能です（_urlopen をモック）。

---

## 設定（kabusys.config.Settings）

重要な設定（settings 経由でアクセス）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env 読み込み:
- プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して決定します
- 読み込み順序: OS 環境 > .env.local (override) > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env パーサは引用符・エスケープ・コメント処理に対応しています。

---

## ディレクトリ構成

リポジトリ内の主なファイル・モジュール:

src/kabusys/
- __init__.py
- config.py                      - 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（取得・保存）
  - news_collector.py           - RSS 収集・前処理・DB保存
  - schema.py                   - DuckDB スキーマ定義 / 初期化
  - pipeline.py                 - 日次 ETL パイプライン
  - calendar_management.py      - マーケットカレンダー管理・ユーティリティ
  - audit.py                    - 監査ログテーブル初期化
  - quality.py                  - データ品質チェック
- strategy/
  - __init__.py                  - 戦略モジュールのエントリプレース（未実装の枠）
- execution/
  - __init__.py                  - 発注 / 実行層のエントリプレース（未実装の枠）
- monitoring/
  - __init__.py                  - 監視用モジュール（未実装の枠）

README.md（このファイル）等

---

## 開発上の注意点 / テスト向けフック

- jquants_client はモジュールレベルの ID トークンキャッシュを持ちます。テスト時は _get_cached_token(force_refresh=True) や get_id_token を直接モックしてください。
- news_collector の HTTP 呼び出しは内部で _urlopen を使っています。テストではこの関数を差し替えて外部通信を防げます。
- DuckDB の接続は init_schema() / get_connection() を通じて扱ってください。":memory:" を使うとインメモリ DB になります。
- すべての DDL は冪等に記述されています。既存のデータベースに対して安全に初期化できますが、DDL 実行は破壊的な変更を行う可能性があるため本番での実行は注意してください。

---

もし README に含めたい追加の手順（CI 設定、Docker Compose、実運用時の運用手順、Slack 通知実装例など）があれば教えてください。必要に応じてサンプル .env.example やユニットテストのテンプレートも用意します。