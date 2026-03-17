# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存、品質チェック・ニュース収集・監査ログを備えた ETL / データ基盤を提供します。

---

## 概要

KabuSys は下記の機能を備えた内部用ライブラリ／パッケージです。

- J-Quants API クライアント（認証・リトライ・レート制御・ページネーション対応）
- DuckDB を用いたスキーマ定義および初期化
- 日次 ETL パイプライン（市場カレンダー → 株価 → 財務データの差分取得・保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集器（SSRF 対策・入力正規化・銘柄抽出・冪等保存）
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上のポイント：
- API レート制限（120 req/min）を守るためのスロットリング
- ネットワーク/HTTP エラーに対する指数バックオフリトライ（401 は自動リフレッシュ）
- DuckDB 側は冪等（ON CONFLICT）で保存
- ニュース処理は SSRF 対策・受信サイズ制限・XML 脆弱性対策（defusedxml）を実装

---

## 主な機能一覧

- data.schema
  - init_schema(db_path) — DuckDB スキーマの初期化
  - get_connection(db_path) — 既存接続の取得
- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl（ETL のエントリ）
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.audit
  - init_audit_schema / init_audit_db（監査ログ用テーブル初期化）
- config
  - 自動 .env 読み込み（プロジェクトルート検出）と Settings オブジェクト（環境変数アクセス）

---

## 動作環境・依存関係

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

実際の依存関係は pyproject.toml / requirements.txt を参照してください（本リポジトリでのパッケージ化に合わせてインストールしてください）。

例（pip）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得
2. 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
3. 依存パッケージをインストール
   pip install duckdb defusedxml
4. 環境変数を準備
   - プロジェクトルートに `.env` を配置すると自動読み込みされます（.git または pyproject.toml を基準にルートを特定）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル（必須）

オプション:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 基本的な使い方

以下は代表的な利用例です。コードスニペットは Python コンソールやスクリプト内でそのまま実行できます。

1) DuckDB スキーマ初期化と接続
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

2) 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())

3) 個別の ETL（価格のみ）を実行
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())

4) ニュース収集
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効コード集合（省略可）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
# results は {source_name: saved_count} の辞書

5) マーケットカレンダーのユーティリティ
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date.today())
next_day = next_trading_day(conn, date.today())

6) 監査テーブルの初期化（既存 conn に追加）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

7) J-Quants のトークンを明示的に取得
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用

---

## 利用上の注意 / 開発メモ

- 自動 .env 読み込み
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動ロードします。
  - テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- API レート制御・リトライ
  - J-Quants クライアントは 120 req/min を遵守するようスロットリングを行います。
  - ネットワーク系のエラーや 429/408/5xx に対して指数バックオフで最大 3 回リトライします。401 はトークンリフレッシュを試みます（1 回）。

- ニュース収集の安全対策
  - RSS フィード取得時はスキーム検証（http/https のみ）、リダイレクト先の検査、プライベートアドレス（SSRF 対策）判定、受信サイズ上限（10MB）などの防御を行っています。
  - XML は defusedxml でパースして脆弱性対策を行います。

- DuckDB に関する注意
  - スキーマ初期化は冪等（IF NOT EXISTS）です。既存 DB に対して再実行しても安全です。
  - init_schema は DB ファイルの親ディレクトリを自動作成します。

- 品質チェック
  - 品質チェックは fail-fast ではなく問題を一覧で返す設計です（呼び出し元での判定を想定）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                   — 環境変数/設定管理
- data/
  - __init__.py
  - schema.py                  — DuckDB スキーマ定義・初期化
  - jquants_client.py          — J-Quants API クライアント（取得・保存）
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
  - calendar_management.py     — カレンダー管理・営業日ユーティリティ
  - quality.py                 — データ品質チェック
  - audit.py                   — 監査ログ用テーブル初期化
- execution/
  - __init__.py                — 発注関連（未実装の骨子）
- strategy/
  - __init__.py                — 戦略関連（拡張ポイント）
- monitoring/
  - __init__.py                — 監視・アラート関連（拡張ポイント）

---

## 開発・拡張のヒント

- strategy や execution 周りは拡張ポイントとしてファイルが用意されています。実際の戦略ロジックやブローカー連携はそこに実装してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な環境変数はテスト側で注入すると良いです。
- NewsCollector のネットワーク入出力はモジュール内の `_urlopen` をモックすることで容易にテスト可能です（SSRF ハンドリングを含む）。

---

この README はリポジトリ内の doc（DataPlatform.md 等）や pyproject.toml が存在する場合はそちらと合わせて参照してください。README の内容は実装状況に合わせて更新してください。