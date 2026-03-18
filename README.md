# KabuSys

日本株向けの自動売買基盤（ライブラリ）です。J-Quants / kabuステーション 等からデータを取得し、DuckDB に保存して ETL、品質チェック、ニュース収集、監査ログを扱うためのモジュール群を提供します。

## プロジェクト概要

KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API から株価・財務・市場カレンダーを安全に取得する
- RSS からニュースを収集し前処理・銘柄紐付けする
- DuckDB 上に三層（Raw / Processed / Feature）＋ Execution / Audit スキーマを初期化・管理する
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実行する
- データ取得処理はレート制御・リトライ・トークン自動更新等を備えている

設計上のポイント:
- API レート制限遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ）と 401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT）で上書き
- RSS 収集は SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ制限等を実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント、取得関数（OHLCV / 財務 / カレンダー）、DuckDB 保存関数
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution テーブル）
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - calendar_management: 市場カレンダー更新と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal / order_request / executions）スキーマ初期化
- config: 環境変数読み込み・設定管理（.env 自動読み込み、必須項目チェック、環境判定フラグ等）
- strategy / execution / monitoring: パッケージプレースホルダ（実装は各自追加）

## 必要条件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- （ネットワークアクセスが必要）J-Quants API トークン、kabu API パスワード、Slack トークン など

pip でのインストール例（プロジェクト直下で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発・配布用にパッケージ化している場合:
# pip install -e .
```

任意で requirements.txt / pyproject.toml に依存を記述してください。

## 環境変数（主な必須項目）

以下は設定モジュールで必須とされる環境変数の例です（.env を推奨）。

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       (必須) — Slack チャンネル ID
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL              — ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探し、
  .env → .env.local の順で自動読み込みします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（概要）

1. Python 3.10+ を用意し仮想環境を作成する
2. 依存パッケージをインストールする（duckdb, defusedxml など）
3. プロジェクトルートに .env を作成する（上記の必須環境変数を設定）
4. DuckDB スキーマを初期化する（例: スクリプト / REPL）
   - data.schema.init_schema() を利用して DB ファイルを作成
5. 日次 ETL / ニュース収集 を実行

例（Python REPL またはスクリプト）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
import datetime

# DuckDB ファイルを初期化
conn = init_schema("data/kabusys.duckdb")

# 当日分の ETL を実行（品質チェック含む）
result = run_daily_etl(conn, target_date=datetime.date.today())
print(result.to_dict())
```

ニュース収集の例:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {"7203", "6758"}）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)
```

監査ログスキーマを追加する:
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

## 使い方（主要 API）

- config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env などで設定にアクセスできます。

- data.schema
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path) -> 既存 DB へ接続

- data.jquants_client
  - get_id_token(refresh_token=None) -> id_token 文字列
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - save_news_symbols(conn, news_id, codes) -> int
  - run_news_collection(conn, sources=None, known_codes=None) -> dict[source->saved_count]

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90) -> 保存レコード数

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path) -> 初期化済み接続

## ディレクトリ構成

（主要なファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py                         # .env/環境変数読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント（取得 + 保存）
    - news_collector.py               # RSS ニュース収集・前処理・DB 保存・銘柄抽出
    - schema.py                       # DuckDB スキーマ定義と初期化
    - pipeline.py                     # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py          # カレンダー管理・営業日ユーティリティ
    - audit.py                        # 監査ログスキーマ（signal/order_request/executions）
    - quality.py                      # データ品質チェック
  - strategy/                          # 戦略関連（プレースホルダ）
    - __init__.py
  - execution/                         # 発注・ブローカー連携（プレースホルダ）
    - __init__.py
  - monitoring/                        # 監視関連（プレースホルダ）
    - __init__.py

（README 上のファイル一覧はソースツリーに基づいています。実際のプロジェクトでは追加のモジュールやスクリプトが存在する場合があります。）

## 運用上の注意点

- J-Quants API のレート制限（120 req/min）を遵守してください。クライアントは内部で固定間隔スロットリングを行いますが、大量同時リクエスト時は注意が必要です。
- id_token の自動リフレッシュが実装されていますが、refresh token は厳重に管理してください。
- DuckDB ファイルのバックアップ・ロックに注意してください（複数プロセスからの同時書き込みは想定外の挙動を招くことがあります）。
- news_collector は SSRF・XML Bomb 等に対策をしていますが、外部 URL を扱う際のリスクは常に存在します。
- production（live）環境では KABUSYS_ENV=live を設定し、ログ・監査・バックアップ運用を検討してください。

## 貢献・拡張

- strategy / execution / monitoring パッケージはプレースホルダです。実際の売買ロジックやブローカー連携はこれらに実装してください。
- 追加のデータソースや外部通知（Slack 通知、可観測化）は既存の設定と統一して実装するとよいです。
- 品質チェック・監査の閾値や挙動は運用に合わせて調整を推奨します。

---

不明点や追加で README に含めたい項目（例: CI, テスト手順、より詳細な .env.example、開発用スクリプトなど）があれば教えてください。必要に応じて追記します。