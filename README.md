# KabuSys

日本株の自動売買プラットフォーム向けライブラリ（プロジェクト骨格）
（J-Quants API からのデータ取得、DuckDB スキーマ、ETL パイプライン、品質チェック、監査ログ等を提供）

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株のデータ取得からデータベース格納、品質チェック、監査ログ（発注〜約定のトレーサビリティ）までをサポートする内部ライブラリ群です。主に以下を提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダーの取得）
- DuckDB を用いたデータスキーマ定義と初期化
- ETL（差分取得・バックフィル・保存）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（シグナル → 発注要求 → 約定のトレース）
- 環境変数ベースの設定管理（自動 .env ロード機能あり）

設計上のポイント：
- J-Quants のレート制限（120 req/min）を守るため固定間隔のレートリミッタを実装
- リトライ／指数バックオフ、401 時のトークン自動リフレッシュを組み込み
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- ETL は差分更新＋backfill により API の後出し修正を吸収
- 品質チェックは Fail-Fast ではなく検出結果をすべて返す方針

---

## 機能一覧

- 環境設定管理
  - .env（および .env.local）をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須設定の取得（未設定時は ValueError）

- データ取得（J-Quants）
  - 日足（OHLCV）取得: fetch_daily_quotes
  - 財務データ（四半期 BS/PL）取得: fetch_financial_statements
  - マーケットカレンダー取得: fetch_market_calendar
  - トークン取得／自動更新: get_id_token

- DuckDB スキーマ管理
  - init_schema(db_path) : 全テーブル（Raw / Processed / Feature / Execution）を作成
  - init_audit_schema(conn) / init_audit_db(path) : 監査ログ用テーブルの初期化
  - get_connection(db_path) : 既存 DB への接続取得

- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別ジョブ
  - run_daily_etl : 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）

- 品質チェック
  - check_missing_data: OHLC 欠損検出
  - check_spike: 前日比スパイク検出
  - check_duplicates: 主キー重複検出
  - check_date_consistency: 未来日付／非営業日データ検出
  - run_all_checks: 上記をまとめて実行

- 監査ログ（order_requests / executions / signal_events 等）
  - 監査レコードを格納する DDL とインデックス定義

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈に | を使用しているため、3.10 以上が推奨される場合があります）
- Git 作業ディレクトリにリポジトリがあること（.env 自動読み込みのルート検出に必要）

1. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール  
   （本リポジトリはパッケージ化前提の構成なので、開発中は editable install が便利）
   必要最小限の依存：duckdb
   ```
   pip install duckdb
   pip install -e .
   ```
   ※ 実運用では HTTP クライアント周りやロギング、Slack 連携等の追加依存が必要になる場合があります。

3. 環境変数の準備
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込みは以下の優先順位：
   OS 環境変数 > .env.local (> .env)
   自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx      # 必須: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD=...               # 必須: kabuステーション API パスワード（発注周りを使う場合）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
   - SLACK_BOT_TOKEN=xoxb-...            # 必須（Slack 通知を使う場合）
   - SLACK_CHANNEL_ID=C0123456789        # 必須（Slack 通知を使う場合）
   - DUCKDB_PATH=data/kabusys.duckdb     # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db      # 任意（監視 DB 用）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env サンプル（.env.example を参考に作成してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は最小限の使い方例です。DuckDB スキーマを初期化し、日次 ETL を実行するサンプルです。

1. Python スクリプト / REPL から実行

   - スキーマ初期化（初回のみ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # またはインメモリ:
   # conn = init_schema(":memory:")
   ```

   - 監査ログスキーマを追加（監査用に別 DB で管理する場合は init_audit_db を使用）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

   - 日次 ETL 実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
   print(result.to_dict())
   ```

   - 個別ジョブ（例：株価のみ）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_prices_etl
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   print(f"fetched={fetched}, saved={saved}")
   ```

2. トークン操作（必要に応じて）
   ```python
   from kabusys.data.jquants_client import get_id_token
   id_token = get_id_token()  # .env に設定したリフレッシュトークンを使う
   ```

3. 品質チェックのみ実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)  # 問題一覧を取得
   for i in issues:
       print(i)
   ```

ログ出力やエラーは Python の logging 設定に従います。LOG_LEVEL 環境変数でレベル制御できます。

---

## 重要な挙動・運用上の注意

- .env 自動読み込み:
  - パッケージ内で .env/.env.local をプロジェクトルートから自動ロードします（CWD でなく __file__ の位置からルート判定）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利）。

- J-Quants API の取り扱い:
  - レート制限は 120 req/min を守るために固定間隔の RateLimiter を利用しています。
  - HTTP エラーやネットワーク障害に対してリトライ（最大 3 回、指数バックオフ）を行います。
  - 401 を受信した場合、自動でリフレッシュトークンから ID トークンを再取得して 1 回だけリトライします。

- DuckDB スキーマ:
  - init_schema は冪等（すでにテーブルがあればスキップ）です。スキーマ変更時は注意してください。
  - 監査ログは UTC タイムゾーンに基づく TIMESTAMP（init_audit_schema は TimeZone='UTC' を設定）。

- ETL の差分更新:
  - デフォルトで backfill_days=3 が設定されており、最終取得日の数日前から再取得して後出し修正を吸収します。
  - 市場カレンダー取得は先に行われ、営業日調整に利用されます（非営業日は過去の直近営業日に調整）。

- 品質チェック:
  - スパイク判定デフォルト閾値は 50%（threshold=0.5）。
  - チェックは全件検出方針（Fail-Fast ではない）で、戻り値に問題の一覧を返します。呼び出し元で重大度に応じて処理を決めてください。

---

## ディレクトリ構成

リポジトリ内に含まれる主要ファイル / モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント + 保存関数
    - schema.py                         # DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py                       # ETL パイプライン（差分更新・backfill・品質チェック）
    - audit.py                          # 監査ログ（signal / order_requests / executions）
    - quality.py                        # データ品質チェック
  - strategy/
    - __init__.py                        # 戦略関連のエントリポイント（骨組み）
  - execution/
    - __init__.py                        # 発注・実行周りのエントリポイント（骨組み）
  - monitoring/
    - __init__.py                        # 監視用モジュール（骨組み）

README 等を含めてプロジェクトルートに .env.example、pyproject.toml 等を用意すると運用がスムーズです。

---

## 開発・拡張のヒント

- 発注周り（kabuステーション連携）や Slack 通知などは settings で必要な鍵を管理できるようになっています。実装時は settings.kabu_api_base_url / settings.kabu_api_password / slack の設定を参照してください。
- テストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして明示的に環境変数を注入すると再現性が高まります。
- ETL の単体テストでは jquants_client の id_token を注入できる設計になっているため、HTTP 呼び出しをモックして検証してください。
- DuckDB のインデックスや DDL はクエリパターンに合わせて追加・調整可能です（_INDEXES 配列を編集）。

---

以上が KabuSys の概要と基本的な使い方です。必要があれば README に「API リファレンス」や「運用手順（cron／コンテナ化）」「ログ収集／監視の具体例」などを追記できます。どの情報を追加しますか？