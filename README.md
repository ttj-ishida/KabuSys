# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム構築のための共通ライブラリ群です。本ライブラリは主に以下を提供します。

- J-Quants API を利用した株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動更新）
- RSS を用いたニュース収集と DuckDB への冪等保存（SSRF・XML 攻撃対策あり）
- DuckDB 用スキーマ定義・初期化ユーティリティ（Raw/Processed/Feature/Execution/Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー操作（営業日判定、次/前営業日取得、夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上、冪等性・トレーサビリティ・セキュリティ（SSRF/ZIP Bomb/XML 爆弾対策）を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制限（120 req/min）, リトライ（指数バックオフ, 401 時の自動リフレッシュ）
- data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, extract_stock_codes, run_news_collection
  - RSS 正規化・トラッキングパラメータ除去・記事ID（SHA-256）で冪等保存
- data.schema
  - init_schema(db_path), get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス作成
- data.pipeline
  - run_daily_etl(conn, ...) — 市場カレンダー、株価、財務の差分ETL + 品質チェック
  - run_prices_etl, run_financials_etl, run_calendar_etl
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - QualityIssue 型で問題を集約
- data.audit
  - init_audit_schema(conn), init_audit_db(db_path) — 監査ログ用スキーマ（UTC タイムゾーン固定）
- 設定管理: kabusys.config.Settings（環境変数から各種設定を取得）

戦略（strategy/）や発注実行（execution/）、監視（monitoring/）向けのパッケージ入口は用意されています（実装はプロジェクトで拡張）。

---

## セットアップ手順

1. Python の準備
   - Python 3.9 以上を推奨（コードは型ヒントで最新版の言語機能を使用している箇所があります）。
2. 依存パッケージのインストール
   - 最低限必要なライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそちらを使用してください）
3. パッケージのインストール（開発時）
   - プロジェクトルートで:
     - pip install -e .
4. 環境変数設定
   - .env をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（Settings にて _require() されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)

例 .env（README 用サンプル — 実運用では安全に保管してください）:
    JQUANTS_REFRESH_TOKEN=your_refresh_token
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=CXXXXXXX
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方（簡単な例）

以下は基本的な初期化・ETL 実行・ニュース収集の例です。

1) DuckDB スキーマ初期化
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
    # またはインメモリ:
    # conn = schema.init_schema(":memory:")

2) 日次 ETL を実行（J-Quants トークンは Settings が参照するため .env を事前にセット）
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

3) ニュース収集ジョブを実行（既知銘柄コードを渡すと銘柄紐付けも行う）
    from kabusys.data.news_collector import run_news_collection
    known_codes = {"7203", "6758", "9999"}  # 例: 有効銘柄コードセット
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)

4) マーケットカレンダー更新（夜間ジョブ）
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print(f"saved: {saved}")

5) 監査 DB 初期化（監査専用 DB）
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

6) データ品質チェック単独実行
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn)
    for i in issues:
        print(i)

7) J-Quants API を直接利用したい場合
    from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()  # settings の refresh token を使用
    records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意:
- run_daily_etl 等は内部で例外を局所処理しつつ進めます。戻り値（ETLResult）の errors / quality_issues を確認して対応してください。
- jquants_client は 120 req/min のレート制御とリトライロジックを内包しています。

---

## 主な公開 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.kabu_api_base_url, settings.slack_bot_token, settings.slack_channel_id, settings.duckdb_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - save_news_symbols(conn, news_id, codes) -> int
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source:int]

- kabusys.data.calendar_management
  - is_trading_day(conn, date), next_trading_day(conn, date), prev_trading_day(conn, date), get_trading_days(conn, start, end), calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイル）

（パッケージ内ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py                      # パッケージ初期化（__version__ = "0.1.0"）
    - config.py                         # 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                       # DuckDB スキーマ定義・init_schema
      - jquants_client.py               # J-Quants API クライアント（fetch/save）
      - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
      - news_collector.py               # RSS ニュース収集と保存
      - calendar_management.py          # 市場カレンダー管理（営業日判定等）
      - quality.py                      # データ品質チェック
      - audit.py                        # 監査ログ（signal/order/execution）
      - audit.py                        # 監査DB初期化
      - pipeline.py
    - strategy/
      - __init__.py                      # 戦略関連のエントリ（拡張ポイント）
    - execution/
      - __init__.py                      # 発注/ブローカー連携用のエントリ（拡張ポイント）
    - monitoring/
      - __init__.py                      # 監視 / メトリクス用（拡張ポイント）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は機密情報を含むため安全に管理してください（Vault 等の使用を推奨）。
- J-Quants のレート制限（120 req/min）に従う設計になっていますが、多数の同時プロセスからのアクセスは避けるか、トークン/レート制御を調整してください。
- ETL 実行結果（ETLResult）の quality_issues と errors を監視し、重大な品質問題があればアラートを上げて手動対応してください。
- DuckDB ファイルはバックアップやローテーションを検討してください（特に監査ログは削除しない方針のため永続化容量に注意）。
- news_collector は外部 URL を取得するため SSRF / プライベートアドレス対策を導入しています。カスタム URL を追加する際も注意してください。

---

## 貢献・拡張ポイント

- strategy/ と execution/ パッケージは拡張ポイントです。独自戦略やブローカー接続を実装して統合できます。
- monitoring/ にメトリクス収集（Prometheus 等）やアラート連携を実装してください。
- News に対する自然言語処理（特徴量抽出、センチメント解析）や AI スコアの生成は features/ai_scores テーブルを利用して実装できます。

---

ライセンスやより詳しい設計ドキュメント（DataPlatform.md 等）がある場合はそちらも参照してください。必要であれば README に追記・改善します。