KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の Python パッケージ kabusys の概要と使い方をまとめたものです。
実装は取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、
リサーチ／ファクター計算、AI（ニュースセンチメント・レジーム判定）などで構成されています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買を目的としたモジュール群です。主な要素は次のとおりです。

- Execution: ブローカーへの発注、注文状態管理、再起動時のリコンシリエーション等
- Monitoring: システム状態・注文滞留・リスク監視、kill flag による安全停止、LINE 通知
- Portfolio: 候補選定・重み計算・単元丸め・リスク調整（セクター制限・レジーム乗数）
- Research: DuckDB を使ったファクター計算（Momentum/Value/Volatility 等）、IC 計算
- AI: ニュースの LLM によるセンチメント評価（OpenAI）、市場レジーム判定
- Tools: Paper Trading 検証レポート出力・Streamlit ダッシュボードなど
- Utilities: 設定読み込み、プロセス優先度設定、etc.

主な機能一覧
-------------
- 起動時の自動リコンシリエーション（再起動後の注文・ポジション整合）
- risk 管理（ドローダウン警告・ポジション数監視）と kill flag による Execution 停止
- SystemMonitor による CPU/Memory/Disk/プロセス・データ鮮度監視（SQLite に永続化）
- TradeMonitor による滞留注文・約定価格異常検知
- AlertManager による LINE プッシュ通知（クールダウン管理）
- Portfolio 建設ロジック（候補選定、等配分・スコア重み・リスクベースの株数算出）
- Research モジュール（DuckDB 接続でのファクター計算、前方リターン・IC 計算）
- AI モジュール（OpenAI を使ったニュースセンチメント -> ai_scores、レジーム判定）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用の独立 DB と検証レポート生成ツール

必要条件（想定）
----------------
- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite3（Python 標準ライブラリ経由で使用）
- インターネット接続（OpenAI API / LINE API を使う場合）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して有効化します。
   例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .\.venv\Scripts\activate   # Windows

2. 必要ライブラリをインストールします（例）。
   pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt があればそれを使ってください。

3. 環境変数（または .env ファイル）の準備:
   - .env または .env.local をプロジェクトルートに置くと自動的に読み込まれます。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（Settings クラスに由来）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定なら通知は送信されない）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の fill 動作（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill flag ファイルパス（デフォルト: data/kill.flag）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）など
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill flag を自動でクリアするか (1=クリア)

DB 初期化
- 多くの起動スクリプト（run_monitoring/run_execution）は起動時に監視用テーブルの存在を保障するため init_monitoring_db() を呼びます。
- DuckDB / SQLite のデータファイルはデフォルトで data/ 以下に作られます（環境変数で変更可）。

使い方（起動コマンド例）
-----------------------
※ いずれも仮想環境有効化済みを前提としています。

- ExecutionEngine（本番 or paper_trading）
  - 本番（デフォルト KABUSYS_ENV=development の場合、settings.env を確認してください）
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（Broker はモックになり、別 DB に書き込まれます）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring（ポーリングループ）
  python -m kabusys.run_monitoring
  - ポーリング間隔を上書きする:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 DB の参照用）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI ツール（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意事項 / 実行時の振る舞い
-------------------------
- run_execution/run_monitoring 起動直後に set_process_priority("high") を試みます（権限によっては失敗してスキップされます）。
- Monitoring は Settings.env にかかわらず監視用の sqlite_path（本番パス）を使用します（監視ログは本番 DB に記録する設計）。
- Paper Trading の場合は発注系データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ツール / スクリプト一覧
-----------------------
- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて MockBroker を切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
- monitoring/streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
- tools/paper_verification_report.py: Paper Trading 検証レポート生成ツール（コマンドライン）

パッケージ API（概要）
--------------------
- kabusys.config.Settings: 環境変数 / .env 管理
- kabusys.monitoring: MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.ai: score_news（ニュース NLP）、regime_detector.score_regime（市場レジーム判定）

ディレクトリ構成
----------------
(主要なファイル・モジュールだけ抜粋)

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env ロード / Settings
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... (broker 接続関連など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - process_priority.py

追加のメモ
---------
- DuckDB は大量の時系列データ（prices_daily / raw_financials / raw_news 等）を高速に集計するために使用されています。Research / AI モジュールは DuckDB 接続を受け取り SQL と Python の組合せで処理します。
- OpenAI/API 呼び出し部分はリトライ／バックオフやレスポンス検証を行い、失敗時に安全にフォールバックする実装になっています（API キーが未設定だと例外を出す箇所もあります）。
- 監視データベーススキーマは monitoring/monitoring_db.py の init_monitoring_db() で作成・マイグレーションされます。

この README はコードベースの要点をまとめたものです。詳細な設計方針やアルゴリズムの説明（PortfolioConstruction.md や StrategyModel.md）や実運用時の運用手順は別ドキュメント（設計書）を参照してください。問題や追加説明が必要であれば教えてください。