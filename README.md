# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
主にデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム運用のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・市場カレンダー等の差分取得（ETL）と DuckDB への冪等保存
- ニュース収集（RSS）→ ニュースNLP（OpenAI）による銘柄別センチメント生成
- 市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 研究用途のファクター生成・統計解析ユーティリティ（モメンタム・ボラ・バリュー等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ初期化と管理
- 設定管理（.env 自動ロード機能、環境変数経由設定取得）

設計上の特徴として、ルックアヘッドバイアスを避ける実装、API 呼び出しに対する堅牢なリトライ／バックオフ、DuckDB を用いた高速なローカル分析基盤、LLM 呼び出しのフェイルセーフ（失敗時はスコアを 0 にフォールバック）などを備えています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（日足・財務・カレンダー等）
  - カレンダー管理: is_trading_day / next_trading_day / get_trading_days / calendar_update_job
  - データ品質: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - ニュース収集: RSS フィード取得・前処理・raw_news への保存ロジック
  - 監査ログ: init_audit_schema / init_audit_db（signal/order_request/executions テーブル）
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出→ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュースで市場レジーム判定→market_regime 保存
  - OpenAI API 呼び出し（gpt-4o-mini を利用した JSON Mode）
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数読み込み（.env 自動ロード機能あり）とアプリ設定取得

---

## セットアップ手順

1. Python 環境準備
   - 推奨: Python 3.10+（ソースコードは型ヒントに union 表記等を使用）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - その他、標準ライブラリ以外の要件がある場合は同様に追加してください。
4. パッケージを開発インストール（プロジェクトルートで）
   - pip install -e .
   - ※ setup.py / pyproject.toml がある場合それに従ってください（このリポジトリの配布形態に依存）
5. 環境変数設定
   - ルートプロジェクトに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必要な主な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須: データ ETL）
     - KABU_API_PASSWORD — kabuステーション API パスワード（注文実行系）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必要に応じて）
     - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（既定: data/monitoring.db）
     - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト development）
     - LOG_LEVEL — one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）
6. データベースディレクトリ作成
   - settings.duckdb_path の親ディレクトリを作成しておく（init_audit_db は自動で親ディレクトリを作成しますが、プロジェクトで管理する場合は事前に作成するとよい）

---

## 使い方（代表的な例）

以下は最低限の利用例です。実運用ではログ出力・エラーハンドリング・スケジューリング等を適切に追加してください。

- 設定読み込み（自動で .env を読みます）
  - from kabusys.config import settings
  - settings.jquants_refresh_token 等で取得可能

- DuckDB 接続を作成して ETL を実行する
  - import duckdb
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントを生成（OpenAI API 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - client_conn = duckdb.connect(str(settings.duckdb_path))
  - written = score_news(client_conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合 OPENAI_API_KEY を参照
  - print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（OpenAI API 必須）
  - from kabusys.ai.regime_detector import score_regime
  - written = score_regime(client_conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログスキーマ初期化 / 専用 DB 作成
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # conn_audit に対して監査ログを書き込む処理を行う

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026, 3, 20))

注意:
- OpenAI 呼び出しは gpt-4o-mini を利用し JSON Mode を期待した出力を行います。レスポンスが不正な場合はフェイルセーフでスコア 0 を返す設計です。
- J-Quants API 呼び出しはレートリミット管理とリトライロジックを備えています。get_id_token() は設定されたリフレッシュトークンから ID トークンを取得します。

---

## 設定（環境変数詳細）

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須: ETL を行う場合)
- KABU_API_PASSWORD (注文API を使う場合)
- OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知を行う場合)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: one of development / paper_trading / live（不正値は例外）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（不正値は例外）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとプロジェクトルートの .env 自動ロードを無効化します（テスト用途等）。

.env ファイルの自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われ、`.env` → `.env.local` の順で読み込みます。OS 環境変数はこれらより優先され、.env.local は既存の OS 環境変数を上書きしません（保護されたキーは上書きされません）。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースNLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の公開
    - calendar_management.py       — 市場カレンダー管理 / calendar_update_job
    - stats.py                     — zscore_normalize 等 (汎用統計)
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS 収集 / 前処理
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/バリュー/ボラ系ファクター
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー等

各モジュールは設計方針コメントが詳細にあり、DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る関数が中心です。これは本番口座や注文 API とは分離された、データ処理・研究用途の安全な設計となっています。

---

## 注意事項 / ベストプラクティス

- ルックアヘッドバイアス回避のため、target_date を明示的に渡す API が多く実装されています。バッチ実行やバックテストで現在時刻を無条件に使用しないよう注意してください。
- OpenAI / J-Quants の API キー・トークンは機密情報です。環境変数や安全なシークレット管理を利用してください。
- DuckDB のスキーマやテーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime / market_calendar 等）は ETL 実行前に作成されている必要があります。schema 初期化用スクリプト（存在する場合）を利用するか、必要な DDL を実行してください。
- ニュース収集では SSRF・XML アタック対策（defusedxml、リダイレクト検査、プライベートIP検査、サイズ上限など）を実装していますが、運用環境の要件に応じて追加の監査を行ってください。

---

## サポート / 貢献

この README はコードベースの要点をまとめたものです。実装や API の詳細は各ソースファイル内の docstring / コメントを参照してください。バグ報告・機能提案はリポジトリの issue にお願いします。

--- 

以上。必要であれば README にサンプル .env.example や起動スクリプト（systemd / cron / Airflow など）の例を追記します。どの情報を追加しますか？