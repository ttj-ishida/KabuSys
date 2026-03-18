# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を中心としたデータレイヤ、J-Quants からのデータ収集クライアント、ETLパイプライン、ニュース収集、ファクター計算・リサーチツール、監査ログ（発注〜約定のトレース）などを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持ったモジュール群を含むパッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたスキーマ定義と冪等な保存（ON CONFLICT 処理）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）および特徴量探索（将来リターン・IC）
- 監査ログ（signal → order_request → executions のトレース）
- 設定は環境変数（.env/.env.local）で管理（自動ロード機構あり）

パッケージバージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local 自動読み込み（起点はプロジェクトルート: .git / pyproject.toml）
  - 必須設定がない場合は明示的なエラー
  - 環境切替: development / paper_trading / live

- Data（DuckDB）
  - スキーマ初期化（raw / processed / feature / execution 層）
  - 冪等保存（raw_prices / raw_financials / market_calendar / raw_news 等）
  - 監査ログ用スキーマ（signal_events / order_requests / executions）

- データ収集（J-Quants）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レート制限（120 req/min）・リトライ・401時のトークン自動更新
  - DuckDB への save_* 関数（ON CONFLICT を利用した上書き）

- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分取得・バックフィルロジック（既存最終日からの再取得）

- ニュース収集
  - RSS 取得・XML パース（defusedxml 使用）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、gzip 保護、記事ID は SHA-256 ハッシュ
  - raw_news / news_symbols への冪等保存

- 研究（Research）
  - calc_momentum / calc_volatility / calc_value（DuckDB の prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日・非営業日のデータ） を検出

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部書式や型ヒントを想定）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全性向上）

1. リポジトリをクローン（もしくはソースを配置）
   git clone <repo-url>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   pip install duckdb defusedxml

   （プロジェクトに他の依存があれば requirements.txt を参照してください）

4. パッケージをインストール（開発モード推奨）
   pip install -e .

5. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を配置して設定できます。
   以下は主な環境変数（必須/任意）:

   - 必須:
     - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN … Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID … Slack 通知チャンネル ID
     - KABU_API_PASSWORD … kabuステーション API パスワード（発注周りを使う場合）

   - 任意 / デフォルトあり:
     - KABUSYS_ENV … development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL … DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD … 1 を設定すると .env の自動読み込みを無効化
     - DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH … 監視DB 等に使用（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL … kabu API ベース（デフォルト: http://localhost:18080/kabusapi）

   .env の自動読み込みはプロジェクトルート（.git か pyproject.toml があるディレクトリ）を基準に行われます。テスト時等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要な例）

以下は一部の典型的な利用例です。

- DuckDB スキーマ初期化と接続

  from kabusys.data import schema
  from kabusys.config import settings

  # settings.duckdb_path は Path 型を返します（.env で DUCKDB_PATH を指定可能）
  conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL の実行

  from kabusys.data import pipeline
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  run_daily_etl は市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック を行い、ETLResult を返します。

- ニュース収集ジョブの実行

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB へ接続
  known_codes = {"7203", "6758", ...}  # 抽出対象コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}

- ファクター計算 / リサーチ関数の実行例

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  from kabusys.data import schema
  import datetime

  conn = schema.get_connection(settings.duckdb_path)
  target_date = datetime.date(2024, 1, 4)

  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)

  # 将来リターンを計算して IC を求める例
  fwd = calc_forward_returns(conn, target_date)
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

- 監査ログ（監査スキーマ初期化）

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

---

## 主要 API / モジュール一覧（概略）

- kabusys.config
  - settings: Settings オブジェクト（環境変数経由で設定値を取得）
  - 自動 .env ロード（.env / .env.local）機能

- kabusys.data
  - schema.init_schema(db_path) / schema.get_connection(db_path)
  - jquants_client: fetch_* / save_*（daily_quotes, financials, market_calendar）
  - pipeline.run_daily_etl: 日次 ETL のエントリポイント
  - news_collector.fetch_rss / save_raw_news / run_news_collection
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - quality: run_all_checks（欠損・重複・スパイク・日付不整合検出）
  - stats.zscore_normalize（特徴量の Z スコア正規化）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize の再エクスポート

- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログスキーマの初期化）

---

## ディレクトリ構成

（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存
    - news_collector.py           # RSS 収集・前処理・DB 保存
    - schema.py                   # DuckDB スキーマ定義と初期化
    - stats.py                    # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                 # ETL パイプライン（run_daily_etl など）
    - features.py                 # 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py      # マーケットカレンダー管理
    - audit.py                    # 監査ログスキーマ
    - etl.py                      # ETL 公開 API（ETLResult 再エクスポート）
    - quality.py                  # 品質チェック
  - research/
    - __init__.py
    - factor_research.py          # momentum/volatility/value の計算
    - feature_exploration.py      # 将来リターン・IC・factor_summary
  - strategy/                      # 戦略関連（未実装の初期パッケージ構成）
  - execution/                     # 発注/約定管理（未実装の初期パッケージ構成）
  - monitoring/                    # 監視・アラート（未実装の初期パッケージ構成）

---

## 注意事項 / トラブルシューティング

- .env 自動読込
  - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env/.env.local を読み込みます。CI やテスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API
  - レート制限（120 req/min）を守るためモジュール内でスロットリングしています。大量取得時は注意してください。
  - get_id_token はリフレッシュトークンから ID トークンを取得します。`JQUANTS_REFRESH_TOKEN` を必ず設定してください。

- DuckDB
  - スキーマ初期化時に親ディレクトリを自動作成します（ファイルベース DB を利用する場合）。
  - ON CONFLICT による冪等保存を前提としています。

- RSS / ニュース収集
  - defusedxml を使用して XML の脆弱性を軽減しています。RSS のリダイレクト先がプライベートIP（SSRF）や非 http(s) の場合は拒否されます。
  - 大きなレスポンス（デフォルト 10MB 超）や gzip 解凍後に上限を超える場合はスキップします。

---

この README はコードベースの主要な使い方と設計方針を簡潔にまとめたものです。各モジュールには詳細な docstring があり、実行時のログと合わせて挙動を理解できます。必要であれば、具体的な CLI/ジョブの実行例やユニットテストの作成手順も追加します。