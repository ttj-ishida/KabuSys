# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質検査、監査ログ、Execution 層のスキーマ定義などを提供します。

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムを構成する基盤モジュール群です。主な役割は次のとおりです。

- J-Quants API からの市場データ（株価日足、財務データ、カレンダー）の取得と DuckDB への保存
- RSS からのニュース収集とテキスト前処理、銘柄コードの抽出
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の定義および初期化
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 環境設定の管理（.env / 環境変数）

設計上の要点：API レート制限順守、リトライ・トークン自動リフレッシュ、冪等操作（ON CONFLICT）、SSRF 対策、XML 脆弱性対策などを組み込んでいます。

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - API レート制御・リトライ・トークンリフレッシュを内蔵
- data/news_collector.py
  - RSS フィード取得（gzip 対応、サイズ制限、SSRF/XML 脆弱性対策）
  - 記事正規化・ID 生成（URL 正規化 → SHA-256 ハッシュ先頭32文字）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁コード）
- data/schema.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema() で DB を初期化
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）のスキーマと初期化
- data/pipeline.py
  - run_daily_etl(): 市場カレンダー → 株価 → 財務 → 品質チェック の日次 ETL
  - 個別 ETL 関数（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/quality.py
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks() による一括実行
- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパー settings（必須キーの検査、env/log_level 判定、パス解決）

---

## 前提・依存

- Python >= 3.10（typing の | 演算子等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- その他、プロジェクトの実行内容によって追加パッケージが必要になる場合があります（例: Slack 通知等）。

依存はプロジェクトの packaging / requirements に従ってインストールしてください。簡易例:

python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはパッケージ配布がある場合: pip install -e .

---

## 環境変数 / 設定

config.Settings 経由で次の環境変数を参照します（必須は _require により例外）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化
- KABUSYS_ENV の値は Settings.is_live / is_paper / is_dev で判定可能

ストレージパス:
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`

自動 .env 読み込み:
- パッケージの __file__ から親ディレクトリを探索してプロジェクトルートを決定（.git または pyproject.toml を基準）
- 自動で `.env`（上書き不可）→ `.env.local`（上書き可）を読み込みます
- テスト等で自動ロードを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

（実際の運用では .env.example を用意して秘密情報は安全に管理してください）

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成してアクティブ化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （パッケージに requirements があれば pip install -r requirements.txt）
4. 環境変数を設定（.env を作成）
   - 必須変数を .env に記載する
5. DuckDB スキーマを初期化
   - Python スクリプトまたは REPL で init_schema を呼び出す（下記を参照）

---

## 使い方（簡易例）

以下は最小限の Python スニペット例です。実際は適切なロギングや例外処理を追加してください。

- DuckDB スキーマ初期化

from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリを作成して初期化

- 監査ログテーブルを追加入力（必要な場合）

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）

from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())

- 個別 ETL（例: 株価のみ）

from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())

- ニュース収集ジョブの実行

from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に利用する有効コードのセット（省略可能）
stats = run_news_collection(conn, sources=None, known_codes=None)
print(stats)

- J-Quants の直接利用（テスト等）

from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings からリフレッシュトークンを使用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点:
- run_daily_etl は内部で API レート制御・リトライを行いますが、実行頻度は J-Quants の利用規約に従ってください
- 大量データ取得時は rate limit（120 req/min）に注意

---

## 開発時のヒント

- 自動 .env 読み込みを無効にする場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールを import してください（テスト時に有用）。
- NewsCollector のネットワークアクセス部分（_urlopen）をモックすることでユニットテストが容易になります。
- DuckDB はファイルベースだが、init_schema に ":memory:" を渡すとインメモリ DB を使用できます（テストで便利）。
- settings.env の有効値:
  - development, paper_trading, live（それ以外は例外）

---

## 目次（主なモジュール / API）

- kabusys.config
  - settings: 各種設定取得プロパティ
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成

以下はリポジトリ内の主要なファイル一覧（src/kabusys 以下）:

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

- data/: データ取得 / ETL / スキーマ / 品質チェック / 監査ログ等の中核実装
- strategy/: 戦略ロジックを配置する領域（将来的な拡張）
- execution/: 発注等 Execution 層の実装領域（将来的な拡張）
- monitoring/: 監視・メトリクス系の実装領域

---

## ライセンス / 注意事項

- 本ドキュメントはコードベースの README の代替です。実運用前に各種設定（API トークン、証券会社 API）や法的/規約上の確認を行ってください。
- 金融資産の取引にはリスクが伴います。本コードを用いて生の資金で取引する場合は十分なテストとリスク管理を行ってください。

---

必要であれば README の英語版や、CI 用の DB 初期化スクリプト、サンプル .env.example を作成します。どの情報を追加しますか？