# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。  
データ取得（J-Quants）、ETL、ニュース収集、マーケットカレンダー管理、監査ログなどを備えたモジュール群を提供します。主に DuckDB をデータ層に使い、戦略／実行層と連携するための基盤機能をまとめています。

## 特徴（概要）
- J-Quants API クライアント（OHLCV、財務、マーケットカレンダー）
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、401 の場合は自動トークンリフレッシュ）
  - 取得日時（fetched_at）を UTC で記録し、Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- RSS ニュース収集（News Collector）
  - トラッキングパラメータ除去、URL 正規化 → 記事ID を SHA-256 の先頭 32 文字で生成（冪等性）
  - SSRF 対策、受信サイズ上限、XML 攻撃防御（defusedxml）
  - raw_news への冪等保存、銘柄コード抽出と news_symbols の紐付け
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、自動バックフィル）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括実行（各ステップは独立に例外処理）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit（監査）層のテーブル定義と初期化
  - インデックスと外部キーを含む冪等初期化
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティを UUID 連鎖で保存
  - 全てのタイムスタンプは UTC 保持を前提

---

## 機能一覧（主な公開 API / 機能）
- 環境設定: kabusys.config.settings
  - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN）
  - .env / .env.local 自動ロード（プロジェクトルート判定）
  - KABUSYS_ENV / LOG_LEVEL バリデーション
- J-Quants クライアント: kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（リフレッシュ）
- ニュース収集: kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - extract_stock_codes, preprocess_text（ユーティリティ）
- スキーマ管理: kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- ETL パイプライン: kabusys.data.pipeline
  - run_daily_etl（マーケットカレンダー、株価、財務、品質チェックの一括実行）
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）
  - get_last_price_date 等のヘルパー
- カレンダー管理: kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチ）
- 監査ログ初期化: kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)
- データ品質チェック: kabusys.data.quality
  - run_all_checks、check_missing_data、check_spike、check_duplicates、check_date_consistency

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | 記法、annotations の使用）
- Git リポジトリ / pyproject.toml を用意している想定（config の自動 .env ロードが動作）

1. ソースをクローン
   - 例: git clone ... && cd プロジェクト

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要な依存パッケージをインストール
   - 最低依存例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r requirements.txt や pip install -e . を使ってください）

4. 環境変数 / .env を準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須キー（最低限）
     - JQUANTS_REFRESH_TOKEN=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABU_API_PASSWORD=...
   - 任意 / デフォルト
     - KABUSYS_ENV=development|paper_trading|live （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...  （デフォルト: INFO）
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
     - SQLITE_PATH=data/monitoring.db

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=./data/kabusys.duckdb
   ```

5. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで実行:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

---

## 使い方（例）

- 環境設定を読む
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで必須値を取得

- スキーマ初期化（DuckDB）
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（マーケットカレンダー・株価・財務・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  - result.to_dict() で詳細を取得できます

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758"}  # 既知の銘柄コードセット
  - stats = run_news_collection(conn, known_codes=known_codes)
  - stats は {source_name: saved_count} の辞書を返す

- 個別に J-Quants データを取得して保存
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  - saved = jq.save_daily_quotes(conn, records)

- 監査ログテーブルを追加する
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)  # 既存 DuckDB 接続に監査テーブルを追加

- カレンダー操作例
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading = is_trading_day(conn, date(2025, 1, 1))
  - next_day = next_trading_day(conn, date(2025, 1, 1))

ログや例外ハンドリングは各関数が内部で行います。run_daily_etl の戻り値（ETLResult）で品質問題やエラーの概要を確認してください。

---

## 環境変数（主なキー）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト等で使用）

---

## ディレクトリ構成（主要ファイル）
src/
- kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動ロード・バリデーション）
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得・保存）
    - news_collector.py  -- RSS ニュース収集・前処理・保存
    - schema.py          -- DuckDB スキーマ定義・初期化
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理と夜間更新ジョブ
    - audit.py           -- 監査ログ（signal/order_request/executions）定義と初期化
    - quality.py         -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    （戦略関連の実装はここに配置）
  - execution/
    - __init__.py
    （実際の注文・ブローカー連携ロジックはここに配置）
  - monitoring/
    - __init__.py
    （監視・メトリクス用モジュール）

プロジェクトルートには .env/.env.local/.env.example、pyproject.toml（または setup.py）、README.md、LICENSE（任意）を置く想定です。

---

## 設計上の注意点・安全機構
- J-Quants クライアントはレート制限・リトライ・トークン自動更新を内包しており、ページネーション対応や取得時刻（fetched_at）の記録により再現性を保ちます。
- ニュース収集は SSRF 対策、XML 攻撃対策、レスポンスサイズ上限、gzip 解凍後のサイズチェック等の防御を実装しています。
- ETL/保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）しており、部分失敗時でも整合性を保ちやすい設計です。
- 品質チェックは Fail-Fast ではなく問題を収集して返す方針です。ETL 実行者（呼び出し側）が結果を評価して運用判断を行ってください。

---

もし README に追加して欲しい内容（例: CI / テスト実行方法、開発フロー、より詳細な API ドキュメントやサンプルワークフロー）があれば教えてください。必要に応じて追記します。