# KabuSys

日本株自動売買プラットフォーム用の内部ライブラリ群。データ収集（J-Quants/API・RSS）、ETL、データ品質検査、DuckDB スキーマ管理、監査ログなどを提供します。

## 概要

KabuSys は日本市場向けに設計されたデータ基盤／ETL／監査モジュールの集合です。J-Quants API から株価・財務・マーケットカレンダーを取得し、DuckDB に冪等に保存します。RSS からニュースを収集して記事と銘柄の紐付けを行い、品質チェックや監査ログ（発注→約定のトレーサビリティ）をサポートします。

設計上のポイント：
- API レート制限・リトライ（指数バックオフ）対応
- データ取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
- DuckDB へは ON CONFLICT 系の冪等保存
- RSS は SSRF/ZipBomb 等を考慮した堅牢な取得処理
- 品質チェックは Fail-Fast ではなく問題を網羅的に収集

## 主な機能一覧

- 環境設定読み込みと管理（.env / 環境変数）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得 / 保存
  - 財務（四半期 BS/PL）取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - トークン自動リフレッシュ、401 リトライ
- RSS ニュース収集（トラッキングパラメータ除去、SSRF対策、Gzip/サイズ制限）
  - raw_news 保存・記事ID生成（正規化URL の SHA-256 先頭32文字）
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）

## セットアップ

前提：
- Python 3.10+（typing の | 演算子などを使用）
- DuckDB を利用するためネイティブ拡張が必要な場合があります

1. リポジトリをチェックアウトし、セットアップ（開発環境）：
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[dev]"  # setup がある場合。なければ必要なパッケージを個別にインストール
   ```

2. 主要依存パッケージ（最低限）:
   - duckdb
   - defusedxml
   - （標準ライブラリ：urllib, json 等）

   例：
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数（最低必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）

   その他任意（デフォルトがあるもの）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は 1 をセット

   .env の自動読み込み:
   - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化（実行例）
   Python REPL やスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリが無ければ自動作成
   ```

   監査ログ専用スキーマを別DBで初期化する場合：
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit_duckdb.duckdb")
   ```

## 使い方（主要ワークフロー）

以下は代表的な利用例です。

1. 日次 ETL を実行して株価・財務・カレンダーを更新し品質チェックを行う：
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック（デフォルト有効）を順に実行します。個別の ETL（run_prices_etl 等）も呼べます。

2. RSS ニュース収集（既存の DuckDB 接続に保存）:
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes は銘柄コードのセット（抽出のため）
   known_codes = {"7203", "6758", "9984"}  # 例
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: 新規保存件数}
   ```

3. J-Quants から株価を直接フェッチして保存する（テスト的に）:
   ```python
   import duckdb
   from kabusys.data import jquants_client as jq
   conn = duckdb.connect(":memory:")
   # 事前にスキーマを作成しておくこと
   # fetch_daily_quotes で取得 -> save_daily_quotes で保存
   records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
   jq.save_daily_quotes(conn, records)
   ```

4. 品質チェックを個別実行する：
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)
   for issue in issues:
       print(issue)
   ```

## 主要 API（関数・挙動抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles) -> 新規挿入記事IDリスト
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=...)

- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

## ディレクトリ構成

リポジトリ内の主要ファイルは次のとおり（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（取得・保存）
    - news_collector.py       - RSS ニュース収集・保存
    - schema.py               - DuckDB スキーマ定義と初期化
    - pipeline.py             - ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  - マーケットカレンダー管理（営業日ロジック）
    - audit.py                - 監査ログスキーマ（signal/order_request/executions）
    - quality.py              - データ品質検査
  - strategy/                  - 戦略関連（未実装：モジュールプレースホルダ）
    - __init__.py
  - execution/                 - 実行（発注）関連（未実装：モジュールプレースホルダ）
    - __init__.py
  - monitoring/                - 監視関連（プレースホルダ）
    - __init__.py

ドキュメントや DataPlatform.md / DataSchema.md 等の仕様ファイルがリポジトリにあれば参照してください（本コードはそれらの設計に基づいて実装されています）。

## 運用上の注意点

- API レート制限を超えないよう _MIN_INTERVAL_SEC を守る実装ですが、外部プロセスから大量リクエストを投げる際は注意してください。
- .env の自動読み込みはプロジェクトルートを探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して制御できます。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップや運用上の配置を検討してください。
- 監査テーブル（audit）は削除しない前提です。スキーマ設計上 ON DELETE RESTRICT を多用しています。
- RSS 取得は外部 URL にアクセスします。SSRF 等の対策は実装されていますが、運用環境でのソース設定には注意してください。

---

不明点や追加で README に含めたい事項（例：CI / テスト実行方法、開発フロー、デプロイ手順など）があれば教えてください。必要に応じてサンプルスクリプトやもっと詳細な運用ガイドを作成します。