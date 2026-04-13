KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのパッケージ群です。本リポジトリには以下の主要機能を含みます。

- 注文作成〜送信〜状態管理を行う ExecutionEngine（ブローカ抽象化により実運用 / Paper Trading 切替可能）
- 監視サブシステム（System / Trade / Risk モニタ）と通知（LINE）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限等）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI を用いたセンチメント集約）および市場レジーム判定
- Streamlit ベースの監視ダッシュボード

注: コードは Python パッケージとして設計されています。設定は環境変数（.env / .env.local）で行います。config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

機能一覧
-------
主な機能（抜粋）:

- execution/
  - 注文管理（OrderManager）、リコンシリエーション（Reconciler）、リスク管理（RiskManager）
  - ブローカ抽象化（BrokerClientFactory）により本番／モック切替が可能
- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor による定期監視
  - MonitoringDB（SQLite）への永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager（LINE Push）と KillSwitch（flag ファイルによる Execution 停止）
  - MonitoringEngine：複数モニタの束ねとポーリング
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- portfolio/
  - 候補選定、等配分・スコア重み、ポジションサイズ計算（単元丸め・aggregate cap 等）
  - セクター上限適用、レジーム乗数算出
- research/
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）、統計サマリ
- ai/
  - news_nlp: raw_news を読み OpenAI で銘柄別センチメントを算出して ai_scores に書込
  - regime_detector: ma200 とマクロニュースを組み合わせて日次レジームを判定
- tools/
  - paper_verification_report: Paper Trading の実行ログ（SQLite）から検証レポートを生成

セットアップ手順
----------------

前提
- Python >= 3.10（型アノテーションの | 演算子などを使用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- 外部パッケージ: psutil, requests, openai, streamlit（ダッシュボードを使う場合）

推奨手順（UNIX 系の例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. data ディレクトリを作成
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成します。例（.env）:

     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development            # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     LOG_LEVEL=INFO
     PAPER_FILL_MODE=instant

   - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします（既存の OS 環境変数は上書きされません）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DB 初期化
   - Monitoring/Execution を起動すると init_monitoring_db が呼ばれて monitoring DB のテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を作成します。手動で作りたい場合は Python コンソールで init_monitoring_db() を呼ぶか、run_monitoring/run_execution を起動してください。

使い方
------

エントリポイント（例）

- 監視ループ（SystemMonitor 単体起動）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。
  - 実行:
    - python -m kabusys.run_monitoring
  - 特徴:
    - プロセス優先度を high に設定（psutil を利用）
    - 監視用 SQLite（Settings.sqlite_path）と DuckDB に接続
    - PID ファイル確認、データ鮮度確認、監視ログを DB に書込

- ExecutionEngine（発注エンジン）起動
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution

- Streamlit ダッシュボード（監視 DB の可視化）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視情報・ポジション・直近注文・リスクログ等を表示

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究 API（コード内関数呼び出し）
  - ニュースセンチメント:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ファクター計算（研究用途、DuckDB 接続を渡す）:
    - kabusys.research.calc_momentum(conn, target_date)
    - kabusys.research.calc_volatility(conn, target_date)
    - kabusys.research.calc_value(conn, target_date)
  - ポートフォリオ構築ユーティリティ:
    - kabusys.portfolio.select_candidates(...)
    - kabusys.portfolio.calc_equal_weights(...)
    - kabusys.portfolio.calc_score_weights(...)
    - kabusys.portfolio.calc_position_sizes(...)
    - kabusys.portfolio.apply_sector_cap(...)
    - kabusys.portfolio.calc_regime_multiplier(...)

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector 用）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
  - paper_trading の場合は paper_trading 用 SQLite に記録され、本番 DB と切り離されます
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH — Execution 用の PID/kill flag のファイルパス
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

ディレクトリ構成
----------------
主要ファイル・ディレクトリの概観（src/kabusys 以下）:

- __init__.py
- config.py  — 環境変数 / .env ロード / Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- execution/
  - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py, order_*...

- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - kill_switch.py, alert_manager.py, monitoring_engine.py
  - streamlit_dashboard.py

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py

- research/
  - factor_research.py, feature_exploration.py

- ai/
  - news_nlp.py, regime_detector.py

- data/ (実行時に生成されることを想定)
  - kabusys.duckdb (DuckDB)
  - monitoring.db (監視 SQLite)
  - paper_trading.db (Paper Trading 用 SQLite)
  - execution.pid, kill.flag

- tools/
  - paper_verification_report.py

注意事項 / 運用メモ
-----------------
- Settings は .env/.env.local の自動読み込み機能を持ちます。OS 環境変数が優先され、.env.local は .env を上書きします。
- Monitoring は常に Settings.sqlite_path（本番 DB パス）を参照しますが、run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して DB を分離します。
- run_* スクリプトは起動時にプロセス優先度を high に変更しようとします。権限がない場合は警告が出ますが処理は継続します。
- OpenAI 呼び出しは外部 API 障害時に適切なフォールバック（0.0 やスキップ）を行うよう設計されていますが、APIキーは必須です（呼び出し先関数で明示的にチェックされます）。
- DuckDB に対する executemany の仕様差分に注意（空リスト渡し不可等）。モジュール内で互換性対策が入っています。
- unit テストやステージングで自動 .env ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を記載してください）

問い合わせ
---------
不明点や実行上の問題があれば、リポジトリの issue を作成するか、プロジェクト管理者へ連絡してください。

以上。