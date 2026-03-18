# KabuSys

日本株向け自動売買プラットフォーム（KabuSys）の軽量実装群。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集、特徴量計算、監査ログ、カレンダー管理、戦略／発注基盤の下地を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構成する共通レイヤー群を提供します。主な役割は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得（レート制限／リトライ／トークン自動リフレッシュ対応）
- DuckDB を用いた永続化スキーマ（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS を用いたニュース収集と銘柄抽出（SSRF 保護・トラッキングパラメータ除去・データ正規化）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と評価ユーティリティ（forward returns, IC, zscore）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（シグナル → 発注 → 約定のトレース可能なスキーマ）

設計方針として、本実装は「DuckDB と標準ライブラリ中心」で、外部ライブラリへの依存を最小化しています（ただし duckdb, defusedxml 等は必要）。

---

## 主な機能一覧

- data/jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制限（120 req/min）・リトライ・ID トークンの自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT ベース）
- data/schema
  - 全テーブルの DDL 定義と init_schema(db_path)
- data/pipeline
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェックの一括処理
  - run_prices_etl, run_financials_etl, run_calendar_etl（差分更新・バックフィル対応）
- data/news_collector
  - fetch_rss / save_raw_news / run_news_collection
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・記事ID は SHA-256 ベース
  - 銘柄コード抽出（4桁コード）
- data/quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data/calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- data/audit
  - 監査用スキーマ（signal_events, order_requests, executions）と init_audit_schema / init_audit_db

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法等を使用）
- pip が利用可能

1. 仮想環境を作る（推奨）
   - macOS/Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール
   - 本リポジトリでは少なくとも次が必要です:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実際はプロジェクトの requirements.txt / pyproject.toml を参照して下さい（本コード断片では示されていません）。

3. リポジトリを editable インストール（開発時）
   ```
   pip install -e .
   ```

4. 環境変数設定
   - .env / .env.local から自動的に読み込まれます（プロジェクトルートに .git または pyproject.toml がある場合）。
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（実行で使う機能により変わる）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で取得／更新に使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知機能を使う場合
   - オプション:
     - KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

6. 監査用 DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡易ガイド・サンプル）

- 日次 ETL を実行する（例: 今日分）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ETL の個別ジョブ（株価・財務・カレンダー）
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  # conn は init_schema で取得した接続
  run_calendar_etl(conn, date.today())
  run_prices_etl(conn, date.today())
  run_financials_etl(conn, date.today())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = init_schema("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2024, 1, 5))
  # recs: list of {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"}
  ```

- forward returns / IC 計算
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  forward = calc_forward_returns(conn, date(2024,1,5))
  # factor_records は独自に用意したファクター結果
  ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- J-Quants からのデータ取得（直接呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- マーケットカレンダーの利用
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_day = is_trading_day(conn, date(2024,1,1))
  next_day = next_trading_day(conn, date(2024,1,1))
  ```

ログレベルは環境変数 LOG_LEVEL で制御します。各モジュールは logging を使用しています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants 認証)
- KABU_API_PASSWORD (必須: kabuステーション を使う場合)
- KABU_API_BASE_URL (任意: デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意: Slack 通知)
- DUCKDB_PATH (任意: デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意)
- KABUSYS_ENV = development | paper_trading | live（デフォルト development）
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 （.env の自動読み込みを無効化）

注意: .env と .env.local の自動読み込みは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。読み込み順は OS 環境変数 > .env.local > .env です。

---

## ディレクトリ構成

（抜粋: 主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - news_collector.py     — RSS ニュース収集・保存
    - schema.py             — DuckDB スキーマ定義 & init_schema
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック
    - calendar_management.py— カレンダー管理（is_trading_day 等）
    - etl.py                — ETL 公開インターフェース（ETLResult 再エクスポート）
    - audit.py              — 監査ログスキーマ初期化
    - features.py           — 特徴量ユーティリティの公開
  - research/
    - __init__.py
    - feature_exploration.py— forward returns / IC / summary
    - factor_research.py    — momentum/value/volatility の計算
  - strategy/
    - __init__.py           — 戦略層のエントリ（空のモジュール）
  - execution/
    - __init__.py           — 発注 / 実行層のエントリ（空のモジュール）
  - monitoring/
    - __init__.py           — 監視関連（空のモジュール）

ドキュメント内にある各モジュールは、DuckDB 接続を受け取る設計になっており、本番環境の発注 API／証券会社接続等へは研究モジュールから直接アクセスしないよう分離されています。

---

## 開発上の注意 / 設計上のポイント

- DuckDB を DB バックエンドに使用し、DDL は冪等（CREATE IF NOT EXISTS）で管理。
- J-Quants クライアントは 120 req/min のレート制限を想定、固定間隔スロットリングで制御。
- ニュース収集では SSRF 対策、gzip サイズ制限、defusedxml を用いた XML パース防御を実装。
- ETL は差分取得 + バックフィルの戦略で API の後出し修正に対応する。
- 品質チェックは Fail-Fast にせず問題を収集して呼び出し側に判断を任せる設計。
- 環境設定は .env/.env.local を自動的に読み込むが、テスト等で無効化可能。

---

## ライセンス / コントリビューション

この README ではライセンス情報は含まれていません。実際のリポジトリでは LICENSE を確認してください。コントリビュートや問題報告は GitHub 等のリポジトリ運用ルールに従って下さい。

---

必要であれば、README にサンプル .env.example、より詳細な CLI／サービス起動方法、ユニットテストの実行手順、依存関係の完全な一覧（pyproject.toml / requirements.txt）を追加します。どの情報を追加しますか？