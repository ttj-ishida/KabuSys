KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買支援ライブラリ／サービス群です。本リポジトリは以下の主要機能群を含みます。

- 注文発行・管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数計算）
- リサーチ（ファクター計算・特徴量探索）
- AI連携（ニュースのセンチメント評価、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- ユーティリティ（環境設定ロード、プロセス優先度設定 等）

設計上のポイント
- DuckDB（prices_daily / raw_financials など）をリサーチ用に使用。発注系は SQLite（monitoring DB / paper_trading DB）で管理。
- 環境変数 / .env ファイルを読み込む Settings モジュールによる設定管理（自動読み込み、.env.local 優先）。
- Paper Trading 用に本番DBと分離された設定が用意されている（KABUSYS_ENV=paper_trading）。
- AI（OpenAI）呼び出しは堅牢なリトライ・バリデーションを実装。API キーは環境変数または引数で指定。

主な機能一覧
---------------
- run_monitoring.py
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用（Settings に依存）。

- run_execution.py
  - ExecutionEngine を起動して取引セッションを実行。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_sqlite_path（デフォルト: data/paper_trading.db）へ記録。

- monitoring
  - MonitoringDB: 監視用 SQLite のスキーマ生成 / 読み書き（init_monitoring_db は冪等）。
  - SystemMonitor: CPU/Mem/Disk、プロセス存在チェック、データ鮮度チェック。
  - TradeMonitor: 注文滞留、約定価格異常チェック。
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新、リスクログ記録。
  - KillSwitch: kill.flag ファイルによる ExecutionEngine 停止シグナル発行。
  - AlertManager: LINE Messaging API を使った通知（トークン未設定時はログのみ）。
  - MonitoringEngine: 上記を束ねてポーリング・アラート／KillSwitch 評価。

- portfolio
  - Portfolio construction: 候補選定、等分配／スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、株数計算（単元丸め、aggregate cap）。

- research
  - factor_research: momentum / volatility / value ファクター計算（DuckDB を使用）。
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリ。

- ai
  - news_nlp.score_news(): raw_news を LLM（gpt-4o-mini を想定）へ送り銘柄ごとにセンチメントを ai_scores テーブルへ書込。
  - regime_detector.score_regime(): ETF とマクロニュースを組合せて市場レジーム判定（bull/neutral/bear）を market_regime テーブルへ書込。

- tools
  - paper_verification_report: Paper Trading の検証レポート生成 CLI（期間指定可）。
  - streamlit_dashboard: Monitoring DB を可視化する Streamlit ダッシュボード。

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈の | 演算子などを使用）
- DuckDB, psutil, requests, openai, streamlit などの外部ライブラリが必要

1. リポジトリをクローン・作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt / poetry / pyproject.toml を使って依存管理してください。

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動読み込みを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な処理がある場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード（Execution 実行時に必要）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager が LINE に通知する場合に必要
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（代表コマンド）
--------------------
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能。

- ExecutionEngine 起動（取引実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH へ保存されます。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
  （DuckDB 接続を用意し、OPENAI_API_KEY を渡すか環境変数を設定してください）

注意点 & 運用ノウハウ
--------------------
- Settings は .env/.env.local の自動読み込みを行います。既に OS 環境変数が存在するキーは上書きされません。
- run_monitoring は Settings.sqlite_path（本番 DB）を常に使用します。監視 DB と実行系 DB を分離したい場合は設定を見直してください。
- monitoring_db.init_monitoring_db は既存 DB へのカラム追加マイグレーション（peak_value, latency_ms）を含み、冪等です。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で停止判定を行う仕組みです。ExecutionEngine 起動時に clear を実装している場合は起動時にフラグをクリアしてください（Settings.kill_flag_clear_on_start を参照）。
- 権限や OS によっては process priority や CPU affinity の設定が失敗することがあります（psutil による警告が出ますが処理は継続します）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                      - パッケージメタ情報
    config.py                        - Settings（環境変数 / .env 読み込み）
    run_monitoring.py                - SystemMonitor ポーリングループ起動
    run_execution.py                 - ExecutionEngine 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                    - ニュースセンチメント評価（OpenAI）
      regime_detector.py             - 市場レジーム判定（ETF + LLM）

    monitoring/
      __init__.py
      monitoring_db.py               - SQLite スキーマ・読み書き
      system_monitor.py              - システム状態 / データ鮮度チェック
      trade_monitor.py               - 注文滞留 / 約定異常監視
      risk_monitor.py                - ドローダウン / ポジション上限監視
      kill_switch.py                 - kill.flag 書き込みユーティリティ
      alert_manager.py               - LINE Push 通知（クールダウンあり）
      monitoring_engine.py           - モニタ群の統括
      streamlit_dashboard.py         - Streamlit ダッシュボード

    execution/
      (OrderManager, Reconciler, ExecutionEngine など) —
      reconciler.py
      order_manager.py
      order_repository.py
      order_record.py
      broker_factory.py
      broker_api.py
      risk_manager.py
      ...（実行系関連ファイル）

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py

    utils/
      __init__.py
      process_priority.py            - プロセス優先度・CPU affinity 設定

data/
  (デフォルトで使われるデータファイル)
  - data/monitoring.db               (Settings.SQLITE_PATH デフォルト)
  - data/kabusys.duckdb              (Settings.DUCKDB_PATH デフォルト)
  - data/paper_trading.db            (Paper Trading 用デフォルト)
  - data/execution.pid               (PID file のデフォルト)
  - data/kill.flag                   (KillSwitch のフラグファイル)

開発 & テスト
--------------
- Settings の自動.env読み込みを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は _call_openai_api 関数を patch / mock することでユニットテスト可能です（各 ai モジュールで明示的に切り出し済み）。
- MonitoringDB によるテーブル作成は冪等なのでテスト用に何度でも初期化できます。

ライセンス / 責務
-----------------
この README はコードベースのドキュメント要約です。実運用の前に以下を確認・実装してください。
- 実ブローカー API の扱い（証拠金、注文の安全性、例外処理の拡充）
- セキュリティ（API キーの管理、アクセス制御）
- 監視とアラートの運用フロー（通知先、オンコール手順）
- 性能・スケーリング要件（DuckDB のファイル管理、バックアップ）

補足
----
README やサンプル .env（.env.example）を用意すると導入ハードルが下がります。必要であれば .env.example のテンプレートも作成しますので指示ください。