# KabuSys

日本株向けの自動売買・データパイプライン基盤 (KabuSys)。  
J-Quants や RSS など外部データソースから市場データ・財務データ・ニュースを取得し、DuckDB に保存・品質チェックを行い、戦略／発注／監査層へ接続するためのライブラリ群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持ったモジュール群で構成されています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS フィードからニュースを安全に収集して DuckDB に保存し、銘柄コードと紐付けるニュースコレクタ
- データ品質チェック（欠損・重複・日付不整合・スパイク検出）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
- 監査ログ（signal → order_request → execution のトレース可能な階層）初期化ユーティリティ

設計上の要点：
- J-Quants API のレート制限（120 req/min）を遵守する RateLimiter を備えます。
- HTTP リトライ（指数バックオフ、最大 3 回）や 401 発生時の自動トークン更新に対応。
- DuckDB への保存は冪等（ON CONFLICT）を意識した実装。
- RSS は SSRF / XML Bomb 等の攻撃対策（スキーム検査、プライベートIPブロック、defusedxml、受信サイズ上限）を実装。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制御・リトライ・トークン自動リフレッシュ

- data.news_collector
  - fetch_rss: RSS 取得（gzip 解凍、XML パース、SSRF 防止）
  - save_raw_news / save_news_symbols / run_news_collection: DuckDB へ冪等保存、銘柄抽出と紐付け
  - URL 正規化、トラッキングパラメータ除去、SHA-256 ベースの記事ID生成

- data.schema
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution テーブル群）
  - init_schema(db_path) / get_connection(db_path)

- data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL 実行: run_daily_etl（品質チェックを含む）

- data.calendar_management
  - 営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - calendar_update_job：JPX カレンダーの差分更新ジョブ

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - QualityIssue 型で問題を集約

- data.audit
  - 監査ログ用スキーマ初期化（signal_events, order_requests, executions）とインデックス

- config
  - .env / 環境変数読み込み、Settings オブジェクトで各種設定を取得

---

## 必要条件 / 依存関係

- Python 3.10 以上（型ヒントの記法等より）
- パッケージ例（最低限）:
  - duckdb
  - defusedxml

※ プロジェクトの実際の requirements.txt がなければ、上記を pip でインストールしてください。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境を作成（任意）
- python -m venv .venv
- source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージをインストール
- pip install -r requirements.txt    （requirements.txt がある場合）
- または最低限:
  - pip install duckdb defusedxml

4. 環境変数の設定
- プロジェクトルート（.git もしくは pyproject.toml が存在するディレクトリ）に .env を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。テストや CI で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨する .env の例（.env.example としてプロジェクトに用意する想定）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
# KABU_API_BASE_URL は任意（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
- Python から data.schema.init_schema() を呼び、DB ファイルを作成します（parent ディレクトリがなければ自動作成）。

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルです。実際にはアプリケーション側でログ出力設定や例外ハンドリングを追加してください。

- DuckDB スキーマ初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants トークンは settings を経由して取得）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())

- 単体で株価データを差分取得して保存

from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")

- RSS ニュース収集ジョブ

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は既知の銘柄コードセット（抽出に利用）。None にすると紐付けをスキップ。
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

- J-Quants の ID トークン取得（必要なとき）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用

- 監査ログスキーマ初期化（監査専用 DB を使う場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数一覧（Settings）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

注意: Settings の必須項目が未設定の場合、アクセス時に ValueError が発生します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                -- 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント（取得 + 保存）
  - news_collector.py      -- RSS ニュース収集・保存・銘柄抽出
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - schema.py              -- DuckDB スキーマ定義・初期化
  - calendar_management.py -- カレンダー管理（営業日判定等）
  - audit.py               -- 監査ログスキーマ初期化
  - quality.py             -- データ品質チェック
- strategy/
  - __init__.py            -- 戦略関連（拡張ポイント）
- execution/
  - __init__.py            -- 発注 / 実行層（拡張ポイント）
- monitoring/
  - __init__.py            -- 監視・メトリクス層（拡張ポイント）

---

## 運用上の留意点 / 設計ポリシー（抜粋）

- J-Quants API のレート制限（120 req/min）を守る必要があるため、jquants_client はスロットリングを行います。大量のページネーションを行う際は処理時間に注意してください。
- DuckDB への保存は ON CONFLICT（UPSERT）を使って冪等性を担保しています。外部から DB を操作する場合はスキーマ互換に注意してください。
- RSS の取得は SSRF や XML 攻撃を考慮し安全策を多く実装していますが、外部ソースの信頼性には注意を払ってください。
- 日次 ETL は品質チェックを行った結果を ETLResult として返します。重大な品質問題が検出された場合の対応（ETL 停止や通知）は呼び出し元で決めてください（Fail-Fast ではなく問題検出後に処理を続ける設計）。
- ローカルテストで環境変数自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（tests 等で有用）。

---

## 開発 / 貢献

- 新しい機能は strategy / execution / monitoring に追加してください。データ層は data 以下に整理されています。
- DB スキーマを変更する際は schema.py と audit.py を更新し、後方互換性を保つことを心がけてください。
- 重要な外部通信（API コール、RSS 取得）には適切なモックエンドポイントを用意し、テストを行ってください。

---

必要であれば README に含めるコマンド例や .env.example の完全なテンプレート、CI 設定例、より詳細な API 使用例 (fetch_* の戻り値構造等) も追加できます。どのような追記が必要か教えてください。