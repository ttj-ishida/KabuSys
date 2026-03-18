# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、DuckDB スキーマ管理、ETL、ニュース収集、ファクター計算、品質チェック、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤を構成するライブラリセットです。主に以下を目的としています。

- J-Quants API からの差分データ取得（株価、財務、マーケットカレンダー）
- DuckDB でのデータ保存・スキーマ管理（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・保存・品質チェック）の自動化
- RSS ベースのニュース収集と記事→銘柄紐付け
- ファクター（モメンタム・ボラティリティ・バリュー等）計算、IC/統計解析
- 発注／約定の監査ログ（監査テーブル群）管理
- 品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- DuckDB を中心に SQL + Python で効率的に処理
- J-Quants API はレート制限（120 req/min）・リトライ・トークンリフレッシュ対応
- ETL は差分更新とバックフィルをサポートし、品質チェックは Fail-Fast ではなく問題を収集する方式

---

## 主な機能一覧

- data/jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（冪等保存）
  - レートリミッタ・リトライ・トークン自動リフレッシュ対応

- data/schema:
  - DuckDB のスキーマ定義と初期化（init_schema）
  - 各層（raw, processed, feature, execution）のテーブル定義、インデックス

- data/pipeline:
  - run_daily_etl: 市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ

- data/news_collector:
  - RSS フィード取得（SSRF 対策・gzip サイズ制限・XML セキュリティ）
  - 記事正規化・ID生成（URL 正規化 → SHA-256）
  - raw_news への冪等保存、news_symbols（記事と銘柄の紐付け）

- data/quality:
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue を返し、ETL 結果で評価可能

- data/stats, data/features:
  - zscore_normalize（クロスセクション Z スコア正規化）

- research:
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials に基づくファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（ファクター評価・IC 計算）

- audit:
  - 監査ログ用スキーマ（signal_events, order_requests, executions 等）
  - init_audit_schema / init_audit_db による初期化

---

## セットアップ手順

前提：
- Python 3.9 以上（typing 標準の union 演算子使用を想定）
- DuckDB を利用するためネイティブビルド環境または whl の利用が必要

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   最低限の依存例：
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用してください）

3. パッケージのインストール（開発中）
   プロジェクトルートから（src レイアウトを想定）:
   ```
   pip install -e .
   ```
   （setup/pyproject があれば上記で editable install できます）

4. 環境変数設定（.env の自動読み込みあり）
   必須環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID

   その他オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   自動 .env ロード:
   - プロジェクトルートにある .env を自動読み込みします（優先順位: OS 環境 > .env.local > .env）。
   - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   サンプル .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```
   監査ログ専用 DB を別途用意する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（基本例）

以下は代表的な使用例です。各関数はモジュールドキュメントを参照してください。

1. 日次 ETL 実行（フルパイプライン）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 価格・財務・カレンダーの個別 ETL
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

   prices_fetched, prices_saved = run_prices_etl(conn, date.today())
   financials_fetched, financials_saved = run_financials_etl(conn, date.today())
   calendar_fetched, calendar_saved = run_calendar_etl(conn, date.today())
   ```

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes: 銘柄コードの集合（抽出時に使用）
   known_codes = {"7203", "6758", "9432"}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

4. ファクター計算・IC 計算
   ```python
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
   from kabusys.data.stats import zscore_normalize

   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

   # 例: mom の mom_1m と fwd の fwd_1d の IC
   ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
   stats = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
   ```

5. J-Quants から生データを直接取得して保存
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

---

## 注意点 / 設計に関する補足

- J-Quants API はレート制限 120 req/min に準拠します（内部でレートリミッタを使用）。大量取得時は待ちが発生します。
- HTTP エラー（408/429/5xx）は指数バックオフでリトライします。401 は自動的にリフレッシュトークンで再取得を試みます（1 回のみ）。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）になるよう実装されています。
- news_collector は SSRF 対策、gzip サイズ上限、XML パースの安全化（defusedxml）等を実施しています。
- ETL の品質チェックは Fail-Fast ではなく、問題を列挙して呼び出し元が判断できるようになっています（QualityIssue 型）。

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント / 保存ロジック
    - news_collector.py             - RSS ニュース収集・正規化・DB 保存
    - schema.py                     - DuckDB スキーマ定義 & init_schema
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - quality.py                    - データ品質チェック
    - stats.py                      - zscore_normalize 等統計ユーティリティ
    - features.py                   - features インターフェース（再エクスポート）
    - calendar_management.py        - カレンダー管理 / 営業日判定 / calendar_update_job
    - audit.py                      - 監査ログスキーマ（order_requests / executions 等）
    - etl.py                        - ETLResult 再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py        - 将来リターン計算 / IC / summary
    - factor_research.py            - momentum / volatility / value 等ファクター
  - strategy/                        - 戦略レイヤー（拡張用）
  - execution/                       - 発注/ブローカー連携（拡張用）
  - monitoring/                      - 監視モジュール（拡張用）

---

## 開発・運用上のヒント

- env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動ロードします。
  - OS 環境変数は保護され、.env.local の override に対しても保護されます。
- テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます（ユニットテスト用途）。
- DuckDB: 初回は init_schema() を必ず実行してください。既存 DB に接続する場合は get_connection() を使用します。
- 監査ログ: 実運用では audit スキーマを別 DB に分けることを推奨します（init_audit_db を利用）。

---

この README はコードベースの現状（各モジュールの docstring / API 設計）から作成しています。実運用向けの詳細（依存パッケージの固定、CI/CD、運用スクリプト、詳しい .env.example、Slack 通知やエラーハンドリング方針など）はプロジェクトポリシーに合わせて追記してください。必要であれば、README に含めるサンプルスクリプトや運用手順（cron / Airflow / GitHub Actions の例）も作成します。