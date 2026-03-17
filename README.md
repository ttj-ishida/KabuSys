# KabuSys

日本株の自動売買プラットフォーム向けデータ基盤・ユーティリティ群（ライブラリ）。  
J-Quants API や RSS フィードからデータを取得し、DuckDB に格納・品質チェック・カレンダー管理・監査ログ等を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API から株価（日次OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
- RSS フィードからニュース記事を収集して DuckDB に保存し、銘柄コードと紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数 / .env の自動読み込みと設定ラッパー

設計上のポイント：
- API レート制限順守（J-Quants: 120 req/min の固定間隔制御）
- リトライ（指数バックオフ、401 時のトークン自動リフレッシュ対応）
- DuckDB へ冪等（ON CONFLICT）で保存
- RSS 収集時の SSRF / XML 攻撃対策・受信サイズ上限管理

---

## 主な機能一覧

- kabusys.config.Settings: 環境変数ベースの設定アクセス（必須キーを検査）
  - 必要な環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
  - 自動 .env ロード（プロジェクトルートの .env / .env.local、無効化フラグあり）
- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存、冪等）
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols
  - URL 正規化・トラッキングパラメータ削除・ID は SHA-256 の先頭 32 文字
  - SSRF 検査、gzip・サイズ制限、defusedxml による XML 防御
- data.schema
  - DuckDB のスキーマ定義と init_schema(db_path)（Raw/Processed/Feature/Execution 層）
- data.pipeline
  - 日次 ETL 実行(run_daily_etl)、個別 ETL(run_prices_etl, run_financials_etl, run_calendar_etl)
  - 差分取得、バックフィル、品質チェック呼び出し
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型で検出結果を返す
- data.audit
  - 監査ログ用テーブル定義・init_audit_schema / init_audit_db

未実装（プレースホルダ）:
- strategy パッケージ、execution パッケージ、monitoring パッケージには初期化ファイルのみ（拡張ポイント）

---

## セットアップ手順

前提: Python 3.9+（コードは typing で | を使うため 3.10+ が望ましい）、git が使える環境

1. リポジトリをクローン（または src 配下をプロジェクトに配置）
   - 例: git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 必要な主な依存: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそれを使用）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（kabusys.config が自動読み込み）。
   - 利用する主なキー（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB スキーマ初期化
   - 例（デフォルトパスを使う場合）:
     - python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"

---

## 使い方（簡単な例）

以下はライブラリの主な使い方例です。実運用ではロギング設定や例外ハンドリング、スケジューラ（cron / Airflow 等）を組み合わせてください。

- DuckDB の初期化（1回）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL の実行（株価・財務・カレンダーの差分取得＋品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_daily_etl(conn)  # デフォルトは今日を対象

- 個別ジョブ
  - カレンダー夜間バッチ:
    - from kabusys.data.calendar_management import calendar_update_job
    - saved = calendar_update_job(conn)
  - ニュース収集:
    - from kabusys.data.news_collector import run_news_collection
    - results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  - 監査テーブル初期化:
    - from kabusys.data.audit import init_audit_schema
    - init_audit_schema(conn)

- J-Quants から直接データを取得（テスト用など）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用
  - rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- 設定アクセス
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

---

## ディレクトリ構成

プロジェクトの主要なファイルと説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数／.env ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、取得、保存）
    - news_collector.py
      - RSS 収集、前処理、DuckDB への保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py
      - マーケットカレンダー管理（判定・バッチ更新）
    - audit.py
      - 監査ログテーブル定義・初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py （戦略実装用プレースホルダ）
  - execution/
    - __init__.py （発注実装用プレースホルダ）
  - monitoring/
    - __init__.py （監視用プレースホルダ）

---

## 実運用上の注意点

- API レート制限やリトライ挙動は jquants_client に実装されていますが、実際の運用量に応じて適切にログ監視・アラートを設定してください。
- DuckDB ファイルは単一プロセスでの使用を想定します。複数プロセスから同時アクセスする場合はロックや別の DB を検討してください。
- RSS 取得では SSRF・XML 脅威対策が入っていますが、外部 URL を扱うためネットワークポリシーの管理をしてください。
- 環境変数（特にトークン・パスワード）は安全に管理してください（Vault 等の利用を推奨）。
- テスト時に .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考: よく使うスニペット

- DB 初期化（対話的）
  - python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"

- 日次 ETL を簡単に叩くスクリプト例（run_etl.py）
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema('data/kabusys.duckdb')
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

---

README の内容はコードベースに基づく概要と使い方の案内です。追加の操作例や CI / デプロイ手順、細かい設定例 (.env.example) をご希望であれば追記します。