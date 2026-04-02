# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価 / 財務 / カレンダー等データの差分取得と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集と OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄単位・マクロ）
- ETF とマクロセンチメントの合成による市場レジーム判定
- リサーチ用のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化／管理

設計上の特徴として、ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）、API リトライ・バックオフ、冪等保存（ON CONFLICT）などに配慮しています。

---

## 主な機能一覧

- データ取得 / ETL
  - jquants_client: J-Quants API 呼び出し、ページネーション、トークン自動リフレッシュ、保存関数（raw_prices, raw_financials, market_calendar）
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質
  - quality.run_all_checks（欠損 / 重複 / スパイク / 日付整合性）
- カレンダー管理
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- ニュース処理 / NLP
  - news_collector.fetch_rss: RSS 取得・前処理（SSRF対策、トラッキングパラメータ除去）
  - ai.news_nlp.score_news: 銘柄単位のニュースセンチメントを OpenAI に投げて ai_scores に保存
  - ai.regime_detector.score_regime: ETF(1321) MA とマクロセンチメントを合成して market_regime を更新
- リサーチ
  - research.factor_research: calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査ログ（発注トレーサビリティ）
  - data.audit.init_audit_db / init_audit_schema（DuckDB に監査テーブルとインデックスを作成）

---

## セットアップ手順

前提:
- Python 3.10 以上（コード内の型注釈や | を利用）
- DuckDB を使用（ローカルファイルまたは :memory:）
- OpenAI API（ニュース NLP / レジーム判定で利用）
- J-Quants アクセス用のリフレッシュトークン

1. ソースコードを取得
   - 通常は Git でクローン / パッケージを配置します。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 以下は主要依存の例（実際の requirements はプロジェクトに合わせて用意してください）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - .env または環境変数で次を設定してください（最低限必要なものを列挙）。
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN: Slack 通知を利用する場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI 呼び出しに使う API キー（score_news / score_regime で使用）
   - 自動 .env ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動で読み込みます。
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベースパス（オプション）
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
   - 変更したい場合は環境変数で DU CKDB_PATH / SQLITE_PATH を設定します。

---

## 使い方（主要な例）

以下はパッケージの主要機能呼び出し例です。実際はロガーの設定や例外処理、API トークンの引き回しを行ってください。

- 設定値を参照する
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env など

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date)  # target_date を省略すると今日

- ニュースのスコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=some_date, api_key="sk-...")  # api_key を渡すか環境変数 OPENAI_API_KEY を利用

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=some_date, api_key="sk-...")

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=some_date)
  - vol = calc_volatility(conn, target_date=some_date)
  - val = calc_value(conn, target_date=some_date)

- ETL 結果の確認
  - from kabusys.data.pipeline import ETLResult
  - result = run_daily_etl(conn)
  - if result.has_errors: logging.warning(result.errors)

- 監査ログスキーマ初期化（監査用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可能

- RSS フィード取得
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意:
- OpenAI 呼び出しは API 料金が発生します。ローカルでテストする場合は各モジュールの _call_openai_api をモックしてください（テスト向けに差し替え可能です）。
- J-Quants とのやりとりではレートリミットとリトライが組み込まれています。API 資格情報の管理に注意してください。

---

## 主要な環境変数一覧

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 if using kabu API): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 if using Slack): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須 if using Slack): Slack 通知先チャンネル ID
- OPENAI_API_KEY (必須 for NLP): OpenAI API キー（score_news / score_regime 等）
- DU CKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL (任意): ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env には .env.example を参考に作成してください（プロジェクト側で用意されている前提）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメント（銘柄別）
    - regime_detector.py            - マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（fetch/save）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        - 市場カレンダー管理 / 営業日ロジック
    - news_collector.py             - RSS 収集・前処理
    - quality.py                    - データ品質チェック
    - stats.py                      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化（signal / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py            - Momentum / Value / Volatility 等
    - feature_exploration.py        - forward returns / IC / summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他モジュール（monitoring / execution / strategy 等のプレースホルダが __all__ に存在）

---

## テスト・開発のヒント

- 自動 .env 読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境を手動で注入できます。
- OpenAI 呼び出しや外部 API はユニットテストではモック推奨:
  - ai.news_nlp._call_openai_api や ai.regime_detector._call_openai_api、data.news_collector._urlopen、jquants_client._request などをパッチしてレスポンスを制御できます。
- DuckDB は :memory: を使用して高速な単体テストが可能:
  - init_audit_db(":memory:") や duckdb.connect(":memory:") を利用してください。

---

## 注意事項（運用上の留意点）

- 本ライブラリはデータ取得・リサーチ用に設計されています。実際の売買を行う場合は、kabu API 連携部（発注ロジック）やリスク管理・負荷テスト・監視を十分に実装した上で運用してください。
- OpenAI / J-Quants 等の外部 API 呼び出しは費用・レート制限があります。運用時はキー管理・レート管理を行ってください。
- DuckDB への書き込みは ON CONFLICT を使った冪等保存が基本ですが、バックアップと監査ログを併用することを推奨します。

---

README に書いてほしい追加項目や、特定の使い方サンプル（ETL の cron 実行例、Slack 通知設定例、kabu 発注フロー例）などがあれば教えてください。必要に応じて追記・サンプルコードを追加します。