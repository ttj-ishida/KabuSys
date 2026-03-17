# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants からのマーケットデータ取得、DuckDB スキーマ定義・初期化、ETL パイプライン、ニュース収集、監査ログ用スキーマなど、戦略実行に必要なデータ基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような要件を満たすデータ基盤／支援ライブラリです。

- J-Quants API から株価（日次 OHLCV）、財務（四半期 BS/PL）、市場カレンダーを取得するクライアントを提供
  - レート制限（120 req/min）やリトライ、トークン自動リフレッシュに対応
  - 取得時刻（fetched_at）を記録して look-ahead bias を排除
  - DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS ベースのニュース収集器（ニュースの前処理、SSRF対策、サイズ制限、記事IDの冪等化）
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定・翌営業日/前営業日取得）
- データ品質チェック（欠損、スパイク、重複、日付不整合の検出）

設計方針としては「冪等性」「安全なネットワーク処理（SSRF・XML攻撃対策）」「効率的な DB バルク処理」「トレース可能な監査ログ」を重視しています。

---

## 主な機能一覧

- jquants_client
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存、冪等）
  - レートリミットとリトライ、401 時の自動リフレッシュ実装
- data.schema
  - DuckDB のスキーマ定義（raw_prices, raw_financials, raw_news, prices_daily, features, signals, orders, trades, positions, audit テーブル等）
  - init_schema(db_path) で DB 初期化
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（カレンダー取得 → 株価 → 財務 → 品質チェック の日次 ETL）
  - 差分更新 / backfill 機能
- data.news_collector
  - fetch_rss（RSS フィード取得、XML パース、前処理、SSRF 防止）
  - save_raw_news / save_news_symbols（DuckDB への冪等保存）
  - extract_stock_codes（本文から 4 桁銘柄コード抽出）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間にカレンダーを差分更新）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（品質チェックの総合実行）
- audit
  - 監査用テーブル（signal_events, order_requests, executions）と初期化関数 init_audit_schema / init_audit_db

セキュリティ／堅牢性: XML の defusedxml 使用、レスポンスサイズ制限、SSRF 対策、トラッキングパラメータ除去など。

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子等を使用）
- pip が利用可能

1. リポジトリをクローン（あるいはソースを配置）

2. 仮想環境を作成して有効化（任意）
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows:
     python -m venv .venv
     .venv\Scripts\activate

3. 必要パッケージをインストール（例）
   - 基本的な依存:
     pip install duckdb defusedxml
   - 実際のプロジェクトでは pyproject.toml / requirements.txt に従ってインストールしてください。
   - 開発時はパッケージを編集可能インストール:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - オプション／デフォルト:
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動ロードを無効化
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

5. データベース初期化
   - DuckDB スキーマを初期化:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（簡易サンプル）

ここでは代表的な使い方を示します。実運用ではログ設定やエラーハンドリング、ジョブスケジューラ（cron や Airflow）等を組み合わせてください。

- DuckDB スキーマ初期化
  python:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（run_daily_etl）
  python:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

  - run_daily_etl は market calendar → prices → financials → 品質チェック の順で実行し、ETLResult を返します。

- ニュース収集ジョブ（RSS 取得 → 保存 → 銘柄紐付け）
  python:
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection

    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コード一覧（例）
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)  # {source_name: 新規保存件数}

- カレンダー更新バッチ
  python:
    from kabusys.data.schema import init_schema
    from kabusys.data.calendar_management import calendar_update_job

    conn = init_schema("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"saved: {saved}")

- 監査ログ（Audit）初期化（監査テーブルを追加）
  python:
    from kabusys.data.schema import init_schema
    from kabusys.data.audit import init_audit_schema

    conn = init_schema("data/kabusys.duckdb")
    init_audit_schema(conn)

- J-Quants API を直接呼ぶ例（テスト用）
  python:
    from kabusys.data import jquants_client as jq
    token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
    quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意:
- jquants_client はレート制限や retry を内包しています。大量リクエスト時は注意してください。
- news_collector の fetch_rss は SSRF 対策・gzip サイズ検証などの安全策を実装しています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（=1）

.env ファイルはプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みされます。読み込み順は OS 環境 > .env.local > .env です。

---

## ディレクトリ構成

主要なファイルと役割は以下の通りです（src/kabusys 以下）:

- __init__.py
  - パッケージ初期化。__version__ など。
- config.py
  - 環境変数管理と Settings クラス（自動 .env ロード、必須変数チェック、env/log_level 判定）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - news_collector.py — RSS ニュース収集・前処理・DB 保存（SSRF/サイズ/重複対策）
  - schema.py — DuckDB スキーマの定義と init_schema/get_connection
  - pipeline.py — ETL パイプライン（差分更新・run_daily_etl 等）
  - calendar_management.py — マーケットカレンダーの管理・営業日判定
  - audit.py — 監査ログ（signal / order_request / executions）テーブル初期化
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py（戦略層用のエントリ、実装は個別に追加）
- execution/
  - __init__.py（発注・ブローカー連携用のエントリ）
- monitoring/
  - __init__.py（監視 / メトリクス関連の実装場所）

（上記は現行コードベースの要点抜粋です。戦略・実行の具体実装箇所は未実装・拡張前提です）

---

## 注意事項 / 運用上のヒント

- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に作られます。適切なバックアップや永続化戦略を用意してください。
- J-Quants API のレート制限（120 req/min）を尊重してください。jquants_client は固定間隔スロットリングを実装していますが、大規模なバックフィルではさらに配慮が必要です。
- ニュース収集は外部 RSS を読み込むため、タイムアウトや例外処理を確実に行ったうえでスケジュール実行してください。
- 本ライブラリは DB のスキーマを作成するため、既存スキーマに影響する場合は事前に確認してください（init_schema は冪等ですが、既存データの互換性は留意）。
- 自動 .env 読み込みはテスト時に副作用となることがあるため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

## 貢献 / 拡張

- 戦略（strategy）や発注ブリッジ（execution）モジュールは拡張を前提としています。戦略ごとの signal 生成やリスク管理、order_request のブリッジ実装を追加してください。
- 監査テーブル（audit）はトレーサビリティにもとづく設計がなされています。オペレーションやコールバックの実装を追加することで実運用に耐える仕組みにできます。
- 品質チェック（quality）は SQL ベースで実装されているため、新たなチェックを SQL で追加することが容易です。

---

README はここまでです。必要であれば以下の追加を作成します：
- .env.example のテンプレート
- 実行スクリプト（cron / systemd / Dockerfile）サンプル
- 具体的なログ設定例（logging 設定）
ご希望があれば教えてください。