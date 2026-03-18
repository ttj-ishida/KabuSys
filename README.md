# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。  
J-Quants API や RSS からデータを収集して DuckDB に格納し、特徴量計算・品質チェック・監査ログといったパイプライン処理を提供します。戦略実行・発注・監視の基盤として利用できるモジュール群を含みます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env または環境変数から設定を自動読み込み（プロジェクトルート検出、自動優先順位）
  - 必須設定が不足すると明示的な例外を投げる

- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限順守（120 req/min）、リトライ・指数バックオフ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）とバックフィル
  - 市場カレンダー・株価・財務データの一括 ETL（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のスキーマを定義・初期化
  - 監査ログ用スキーマ（signal → order_request → execution のトレース）

- ニュース収集
  - RSS 取得・前処理・記事ID生成（URL 正規化 + SHA-256）・冪等保存
  - SSRF 対策、受信サイズ上限、Gzip 対応
  - 記事と銘柄コードの紐付け（テキストから銘柄コード抽出）

- 研究用ユーティリティ（Research）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB の prices_daily / raw_financials に依存）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- セキュリティと運用上の配慮
  - 外部リソースの取り扱いで安全対策（XML の defusedxml、SSRF ドメイン検査、gzip 解凍のサイズ検査など）
  - 全てのタイムスタンプの UTC 一貫保存（監査テーブル初期化時に TimeZone を UTC に設定）

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法（X | Y）を使用しているため）
- pip, virtualenv（任意）
- ライブラリ（主要）
  - duckdb
  - defusedxml

実行環境に合わせて追加で HTTP クライアント / 実行用の依存が必要になる可能性があります（例: kabuステーション API を使う場合のライブラリなど）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール

   必要最小限の例:

   ```bash
   pip install duckdb defusedxml
   ```

   開発用にパッケージ化している場合はプロジェクトルートで:

   ```bash
   pip install -e .
   ```

3. 環境変数を設定

   プロジェクトルートに `.env` を置くか、OS 環境変数で設定してください。自動読み込みはデフォルトで有効です（ENV 変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   例: `.env`（必要な変数）

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用（必須）
   - DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（デフォルトあり）
   - KABUSYS_ENV: development / paper_trading / live のいずれか
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

4. DuckDB スキーマ初期化

   デフォルトの `DUCKDB_PATH` を使用する例:

   ```bash
   python - <<'PY'
   from kabusys.data.schema import init_schema, settings
   from kabusys.config import settings as cfg
   # 例: cfg.duckdb_path で指定されたパスに DB を作成してスキーマ初期化
   conn = init_schema(cfg.duckdb_path)
   print("initialized:", cfg.duckdb_path)
   conn.close()
   PY
   ```

   または直接パスを指定:

   ```bash
   python - <<'PY'
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   PY
   ```

---

## 使い方（代表的な操作例）

以下は Python REPL / スクリプトでの利用例です。

1. 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   conn.close()
   ```

   - run_daily_etl は ETLResult を返し、取得件数・保存件数・品質問題・エラーを含みます。

2. ニュース収集ジョブを実行する

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes を渡すと記事と銘柄紐付けを行う
   known_codes = {"7203", "6758", "9984"}  # 例
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

3. J-Quants API から日次株価を直接フェッチして保存する

   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   # id_token を省略すると内部キャッシュを使用（自動リフレッシュ対応）
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print("fetched:", len(records), "saved:", saved)
   conn.close()
   ```

4. 研究用ファクター計算（例: Momentum）

   ```python
   from kabusys.research import calc_momentum
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   res = calc_momentum(conn, target_date=date(2024,1,31))
   # res は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
   print(len(res))
   conn.close()
   ```

5. DuckDB 接続の取得

   - 新規に初期化済み DB を作る: init_schema(path) を使用
   - 既存 DB に接続するだけ: get_connection(path) を使用（スキーマ初期化は行わない）

---

## 設定（settings）について

設定は `kabusys.config.Settings` からアクセスできます。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token / slack_channel_id: Slack 通知設定（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLite モニタリング DB（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（INFO 等）
- is_live / is_paper / is_dev: 環境判定ユーティリティ

環境変数が不足している場合、Settings の必須プロパティは例外を投げます。

---

## よく使うモジュール／API の一覧

- kabusys.config
  - settings: 環境設定オブジェクト

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source)
  - run_news_collection(conn, sources, known_codes)
  - save_raw_news(conn, articles)
  - extract_stock_codes(text, known_codes)

- kabusys.data.quality
  - run_all_checks(conn, ...)

- kabusys.research
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize (via kabusys.data.stats)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント
    - news_collector.py         -- RSS ニュース収集
    - schema.py                 -- DuckDB スキーマ定義 / init_schema
    - stats.py                  -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - features.py               -- 特徴量ユーティリティ公開インターフェース
    - calendar_management.py    -- 市場カレンダー管理 / ジョブ
    - audit.py                  -- 監査ログスキーマ（signal / order_request / executions）
    - etl.py                    -- ETL 公開 API (ETLResult 再エクスポート)
    - quality.py                -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py    -- 将来リターン / IC / summary
    - factor_research.py        -- Momentum / Value / Volatility 計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 運用上の注意 / ベストプラクティス

- 実口座での発注や、kabuステーションと接続する際は `KABUSYS_ENV` を正しく設定し、必ず paper_trading で十分にテストしてください。
- .env に機密情報を置く場合は適切なアクセス制御を行い、リポジトリにコミットしないでください。
- J-Quants の API レート制限やレスポンスの不整合（後出し修正）を考慮して、ETL は差分取得 + バックフィル（デフォルト3日）を行うよう設計されています。バックフィル日数は運用に合わせて調整してください。
- ニュース取得では SSRF 対策／受信上限を実装していますが、外部 RSS ソースの信頼性は様々です。未知ソースは事前検証を行ってください。
- DuckDB のバージョン差異や機能制限（例: ON DELETE CASCADE の一部未サポート）に留意してください。コード内にも注記があります。

---

## 追加情報 / 今後の拡張案

- 実取引の注文送信モジュール（kabuステーション接続）の具現化とテスト
- ストラテジとリスク管理のテンプレート（strategy 層）
- モニタリング・アラート（Slack 連携）の実装例
- Docker コンテナ化と CI/CD の導入

---

必要であれば、README に含めるサンプルスクリプトや .env.example ファイルのテンプレート、さらに詳しい API ドキュメント（各関数のパラメータ説明や例）を追記します。どの部分を拡張しましょうか？