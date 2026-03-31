# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログなどの機能を提供します。

## 特徴（概要）
- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と記事前処理、銘柄紐付け機能
- OpenAI を使ったニュースセンチメント分析（銘柄ごと / マクロ判定）
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ
- 市場カレンダー（JPX）管理と営業日計算ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）

---

## 主な機能一覧
- data/jquants_client.py:
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - 認証トークン管理・レートリミット・リトライ対応
- data/pipeline.py:
  - 日次 ETL（run_daily_etl）、個別 ETL ジョブ（run_prices_etl 等）
  - ETL 結果を表す ETLResult
- data/quality.py:
  - 欠損、重複、スパイク、日付不整合などの品質チェック（run_all_checks）
- data/news_collector.py:
  - RSS 取得、URL 正規化、記事 ID 生成、前処理、SSRF 対策、gzip 制限
- data/calendar_management.py:
  - market_calendar の管理、営業日判定・前後営業日取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
- data/audit.py:
  - 監査ログ用テーブルの DDL と初期化（init_audit_schema / init_audit_db）
- ai/news_nlp.py:
  - 銘柄ごとのニュースセンチメントを OpenAI により算出し ai_scores テーブルへ保存（score_news）
- ai/regime_detector.py:
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- research/*:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC 計算・統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py:
  - 環境変数読み込み（.env 自動読み込み / .env.local 優先）
  - settings オブジェクト経由で設定を参照

---

## 動作要件（推奨）
- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他 標準ライブラリのみで多くを実装していますが、上記は明示的に使用しているライブラリです）

インストール時に依存関係を明示する setup / pyproject を用意している場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクトに pyproject / requirements があればそれを使う

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を配置できます。
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（少なくとも以下のいずれかは利用する機能によって必要）
     - JQUANTS_REFRESH_TOKEN
     - OPENAI_API_KEY
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|... ) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

例 .env (簡易)
- JQUANTS_REFRESH_TOKEN=xxx
- OPENAI_API_KEY=sk-xxx
- DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単なコード例）

以下は各主要機能の使い方例です。実運用ではエラーハンドリング・ログ設定・API キー管理を適切に行ってください。

- DuckDB 接続（例）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 個別 ETL（価格）
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))

- ニュース収集（RSS 取得）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - for a in articles: print(a["id"], a["title"])

- ニュース NLP（銘柄ごとのスコアリング）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026,3,20))
  - print("書き込んだ銘柄数:", n_written)
  - ※ OPENAI_API_KEY が必要（api_key 引数で上書き可能）

- マクロレジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))
  - ※ OPENAI_API_KEY が必要。score_regime は prices_daily / raw_news / market_regime テーブルを参照・更新します。

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - → 監査テーブル群が作成されます

- 市場カレンダー・営業日計算
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading_day(conn, date(2026,3,20))
  - next_trading_day(conn, date(2026,3,20))

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須: J-Quants 利用時）
- OPENAI_API_KEY: OpenAI API キー（必須: AI 系機能利用時）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注などを行う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定（監視等で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視DB等で使う SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment（development/paper_trading/live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

環境変数は .env ファイルまたは OS 環境に設定できます。パッケージは起動時にプロジェクトルートから自動で .env/.env.local を読み込みます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 主要ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境設定・.env 自動読み込み・settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄ごと）
    - regime_detector.py — マクロセンチメント + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 型再エクスポート
    - calendar_management.py — 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py — データ品質チェック
    - news_collector.py — RSS 取得・前処理・保存支援
    - audit.py — 監査ログスキーマ初期化（init_audit_db / init_audit_schema）
    - stats.py — 基本統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - research/（補助モジュール）

---

## 注意事項 / 運用時のヒント
- ファイル/DB パスのデフォルトは `data/` 以下を使います。運用時は適切な永続ストレージを指定してください。
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・フェイルセーフが入っていますが、API キーやネットワーク障害に注意してください。
- DuckDB の executemany に空リストを渡すと問題があるバージョンがあるため、内部実装で空チェックを行っています。DB 操作時の互換性に注意してください。
- run_daily_etl は内部で市場カレンダーを使って target_date を営業日に調整します（calendar を先に取得）。
- テスト用に OpenAI 呼び出しや内部関数をモックすることを想定した設計になっています（ユニットテストが容易）。

---

もし README に追記したい具体的な利用シナリオ（例: バックテスト連携、kabu ステーション発注統合、Slack 通知設定など）があれば、その用途に合わせたサンプルと運用手順を追加します。必要なら書き方（英語版 / より簡潔な導入ガイド等）も作成可能です。