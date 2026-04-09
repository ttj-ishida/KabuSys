KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買の基盤を提供する Python パッケージです。  
主な目的は以下の通りです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- ニュース収集・前処理と LLM によるニュースセンチメント解析
- 市場レジーム判定（ETF MA とマクロニュースを組み合わせ）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェックと監査（監査ログ／注文フローのテーブル定義）
- DuckDB を中心としたローカルデータ保存、冪等な保存ロジック

本 README はパッケージの主要機能・セットアップ・基本的な使い方およびディレクトリ構成をまとめたものです。

主な機能
--------
- ETL（kabusys.data.pipeline）
  - run_daily_etl を中心とした日次差分取得（株価 / 財務 / カレンダー）
  - J-Quants クライアント（kabusys.data.jquants_client）: レート制限、リトライ、トークン自動リフレッシュ対応
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチで送信、ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / forward returns / IC / 統計サマリ等
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などを検出
- 監査（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、環境変数経由の設定 API

前提
----
- Python 3.10 以上（型記法（X | None）を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存パッケージ

セットアップ手順
----------------
1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ 実運用や開発で追加の依存が必要になる場合があります（例: requests 等）。プロジェクトの requirements.txt / pyproject.toml があればそちらを参照してください。

3. パッケージをローカルにインストール（開発モード）
   - pip install -e .

環境変数 / .env
----------------
kabusys.config.Settings から各種設定値を参照します。代表的な環境変数:

必須（使用する機能に応じて必須となるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション等を利用する場合のパスワード

オプション / デフォルトあり
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp / regime_detector）で使用。関数引数でも渡せます。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知
- DUCKDB_PATH: DuckDB 保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の振る舞い（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT など監視関連
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

自動 .env 読み込み:
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）を探し、.env（優先度低）と .env.local（優先）を自動で読み込みます。
- 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

基本的な使い方（コード例）
-------------------------

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクト（fetched / saved / quality_issues / errors を含む）

- ニュースセンチメント（1日分）を生成する
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key は省略可（環境変数参照）

- 市場レジームを判定して保存する
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ用 DB を初期化する
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成

- リサーチ用関数
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  - mom = calc_momentum(conn, target_date=date(2026,3,20))

よくあるトラブルと注意点
----------------------
- OPENAI_API_KEY が未設定だと news_nlp.score_news / regime_detector.score_regime は ValueError を送出します（api_key 引数で注入可）。
- DuckDB パスの親ディレクトリは自動作成されますが、ファイルパーミッションやパスの誤りに注意してください。
- J-Quants API はレート制限（120 req/min）を考慮した実装になっています。大量一括リクエストをする場合は ETL やスケジューリングを調整してください。
- news_collector は RSS の SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）等を実装していますが、実運用では追加のモニタリングとログが推奨されます。
- init_audit_schema は transactional フラグの挙動に注意（DuckDB のトランザクション特性）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はパッケージ内の主要モジュール / ファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP / スコアリング
    - regime_detector.py              — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save）
    - pipeline.py                     — ETL パイプライン
    - quality.py                      — データ品質チェック
    - calendar_management.py          — マーケットカレンダー管理
    - news_collector.py               — RSS ニュース収集・前処理
    - audit.py                        — 監査ログ（DDL・初期化）
    - stats.py                        — 共通統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラティリティ/バリュー算出
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ

開発貢献 / テスト
-----------------
- ユニットテストは各モジュールの外部依存（OpenAI / HTTP / DuckDB）をモックして実装することが想定されています。
- 環境変数の自動読み込みを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp / regime_detector の OpenAI 呼び出しは内部で別関数（_call_openai_api）にまとめられており、テストで差し替え可能です（unittest.mock.patch 等）。

補足
----
- 本 README はコードベースの現状実装に基づく概要ドキュメントです。実運用時はセキュリティ（API キー管理、ネットワークアクセス制御）、監視、ログローテーション、バックアップ等を別途構築してください。
- 実際の依存関係、CI 設定、コマンドラインツールやサンプルスクリプトはプロジェクトの pyproject.toml / requirements.txt / scripts 配下を参照してください（本スナペットには含まれていません）。

必要であれば、実際の .env.example のテンプレート、よく使う CLI スクリプト例、ETL の Cron / Airflow 連携方法、あるいは各関数のより詳細な使用例（引数説明付き）を追加で作成します。どれを優先しますか？