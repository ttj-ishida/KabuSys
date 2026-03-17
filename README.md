# KabuSys

日本株向けの自動売買基盤ライブラリ（データ取得・ETL・品質検査・監査ログ・ニュース収集など）。  
J‑Quants API や RSS フィードからデータを収集し、DuckDB に整備されたスキーマで永続化・検査・活用できるようにすることを目的としています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を提供します。

- J‑Quants API クライアント（株価・財務データ・市場カレンダー）
  - レート制限、リトライ、トークン自動リフレッシュ、fetched_at のトレース等に対応
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェックを含む日次ETL）
- ニュース収集モジュール（RSS 取得、正規化、DuckDB への冪等保存、銘柄紐付け）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境設定読み込み（プロジェクトルートの `.env` / `.env.local` 自動読み込み、必要な環境変数は Settings 経由で取得）

設計における主な配慮点：
- 冪等性（DB 挿入は ON CONFLICT を利用）
- Look‑ahead bias 防止（fetched_at の記録等）
- セキュリティ（RSS の SSRF 対策、defusedxml の利用、受信サイズ制限）
- テストしやすさ（id_token 注入等）

---

## 機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（自動リフレッシュ対応）
  - DuckDB への保存関数（save_*）
  - レートリミット（120 req/min）とリトライ（指数バックオフ）対応

- data/news_collector.py
  - RSS の取得・パース（gzip, defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、記事ID（SHA‑256）生成
  - SSRF リダイレクト検査、受信上限バイト数制限
  - raw_news / news_symbols への冪等保存（トランザクション & INSERT ... RETURNING）

- data/schema.py
  - DuckDB 用テーブル定義（Raw / Processed / Feature / Execution の各層）
  - init_schema(db_path) による初期化

- data/pipeline.py
  - 差分更新ロジックを持つ run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の順で実行し ETLResult を返す

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間更新ジョブ

- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行

- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）定義と初期化

- config.py
  - .env 自動読み込み（プロジェクトルート判定）
  - Settings クラス: 必須環境変数取得と型変換ヘルパ
  - 環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

---

## 必要条件 / 依存

- Python 3.10+
  - （コードに match 文はないが、型ヒントで `X | None` を使用しているため 3.10 以降を想定）
- 必須ライブラリの例（プロジェクトのパッケージ管理に合わせて導入してください）
  - duckdb
  - defusedxml

例（最低限）:
pip install duckdb defusedxml

※ Slack や HTTP クライアントなど他の外部サービスは環境変数に応じて別途導入・設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）
4. 環境変数を準備
   - プロジェクトルートに `.env` を作成すると、自動的に読み込まれます（.env.local は .env を上書き）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env（必須値）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

任意:
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（Python REPL またはスクリプトで実行）
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

監査ログ専用スキーマを追加する場合:
from kabusys.data import audit
audit.init_audit_schema(conn)

---

## 使い方（簡単な例）

- DuckDB スキーマを初期化して日次 ETL を実行する:
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（最初に一度）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（今日分を取得・保存）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

- ニュース収集を行う:
from kabusys.data import schema, news_collector

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes に銘柄コードセットを渡すと銘柄紐付けが行われる
known_codes = {"7203", "6758", "9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)

- J‑Quants から単独で株価を取得して保存する（テスト目的）:
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect(":memory:")
jq.save_daily_quotes(conn, jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5)))

- カレンダー更新ジョブ:
from kabusys.data import calendar_management, schema
conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")

- 設定値の取得:
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)

注意: J‑Quants API 呼び出しは ID トークンが必要です。settings.jquants_refresh_token を .env に設定してください。get_id_token は内部で自動取得/更新を行います。

---

## 自動 .env 読み込みの挙動

- パッケージがインポートされると、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            -- J‑Quants API クライアント & 保存処理
  - news_collector.py            -- RSS ニュース収集 / 正規化 / 保存
  - schema.py                    -- DuckDB スキーマ定義・初期化
  - pipeline.py                  -- ETL パイプライン（日次 ETL 等）
  - calendar_management.py       -- マーケットカレンダー管理（営業日ロジック）
  - audit.py                     -- 監査ログ（signal / order_request / execution）
  - quality.py                   -- データ品質チェック
- strategy/
  - __init__.py                  -- 戦略関連（将来的に実装）
- execution/
  - __init__.py                  -- 発注・約定・ブローカー連携（将来的に実装）
- monitoring/
  - __init__.py                  -- モニタリング関連（将来的に実装）

ドキュメント参照（プロジェクトに存在する場合）:
- DataPlatform.md, DataSchema.md などの設計ドキュメントを参照してください（このリポジトリ内に含まれている想定）。

---

## 開発上の注意 / 補足

- 型・ SQL の扱い:
  - DuckDB の日付/タイムスタンプはコード内で date / datetime に変換していますが、実行環境の DuckDB バージョンにより挙動が異なる場合があります。
- セキュリティ:
  - news_collector はリダイレクト先や最終ホストがプライベートアドレスの場合は接続を拒否します（SSRF 対策）。
  - RSS の XML 解析には defusedxml を使用しています。
- テスト:
  - ネットワークや外部 API の呼び出し箇所はモック可能な設計（例: _urlopen を差し替え）になっています。
- ログ:
  - LOG_LEVEL 環境変数でログレベルを制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

必要に応じて README に追記・修正します。実運用で必要な追加情報（CI/デプロイ手順、サンプル .env.example、ライセンス等）があれば教えてください。