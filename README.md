KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ基盤向けの軽量フレームワークです。  
主な役割は以下の通りです。

- 証券ブローカー（kabuステーション / モック）を用いた ExecutionEngine（発注）  
- システム・発注・リスク監視（Monitoring）と Kill Switch（停止フラグ）  
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）  
- ファクター計算・特徴量探索（Research / DuckDB を利用）  
- ニュース NLP（OpenAI）を用いた銘柄別センチメント付与と市場レジーム判定  
- 開発支援ツール（.env ウィザード・設定検証・ペーパートレード検証レポート）

主要な設計方針
- DuckDB（分析用）＋ SQLite（監視 / 発注ログ）を利用する分離設計  
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）  
- .env / .env.local を自動読み込み（無効化可）  
- ログはコンソールと日次ローテーションのファイル出力（logs/*.log）  

機能一覧
--------
- ExecutionEngine：ブローカークライアントを通した発注実行、OrderManager / RiskManager / Reconciler を統合  
- Monitoring：SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視、Kill Switch 評価、Alert 発信（LINE 等）  
- Portfolio：候補選定 (select_candidates)、等重/スコア重み計算、ポジションサイズ決定（単元株丸め、aggregate cap）  
- Research：momentum / volatility / value 等のファクター計算、将来リターン・IC 計算、ファクター統計要約  
- AI：news_nlp（OpenAI による銘柄別センチメント）、regime_detector（ETF MA とマクロニュースで市場レジーム判定）  
- ツール：.env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading レポート生成（tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10+（typing 機能を一部使用）を想定
- システム依存ライブラリ: duckdb, psutil, openai
- （オプション）PyYAML（config/*.yaml の内容検証用）

例：依存ライブラリのインストール（プロジェクトに requirements.txt があればそちらを使用）
- pip install duckdb psutil openai pyyaml

プロジェクト初期化
1. リポジトリをクローン／展開する  
2. .env ファイルを用意する（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
3. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

主な環境変数（重要／代表例）
- JQUANTS_REFRESH_TOKEN (必須)  
- KABU_API_PASSWORD (必須)  
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development  
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb  
- SQLITE_PATH — デフォルト: data/monitoring.db（Monitoring 用）  
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（default: data/paper_trading.db）  
- LOG_LEVEL — デフォルト: INFO  
- OPENAI_API_KEY — news_nlp / regime_detector を使う場合に必要  
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）。default: 60（run_monitoring 用）  
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production は 0 推奨）

注意:
- .env は機密情報を含むため Git にコミットしないでください（config_setup でも警告あり）。
- 自動 .env 読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方
------
起動スクリプト（コマンドライン例）
- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行中、data/execution.pid に PID が書かれる（設定で変更可）
  - 停止は data/stop_requested.flag を作成（run_execution と run_monitoring は同様の停止フラグを監視）
- Monitoring を起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
  - 監視は常に sqlite_path（本番監視 DB）を使用する点に注意
- .env ウィザード（対話で .env を作成）
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート（SQLite を指定可）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI / Research API（Python から直接呼び出す）
- ニュース NLP（ai_scores 更新）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")  # conn は duckdb connection
- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

監視・停止フラグ
- run_monitoring / run_execution は data/stop_requested.flag を監視して、存在すると安全終了します。
- Kill Switch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（Monitoring 内で評価）。

ログ
- ログは stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- ログディレクトリは LOG_DIR 環境変数で上書き可。デフォルトは logs/

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要なモジュール一覧（抜粋）です。

- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — Monitoring ポーリング起動スクリプト
- config.py                   — Settings / 環境変数読み込みロジック（.env 自動読み込み含む）
- config_setup.py             — .env 対話ウィザード CLI
- validate_config.py          — 起動前設定検証 CLI

パッケージ構成（サブパッケージ）
- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py (prices / raw_financials 取得関連など)
    - stats.py (zscore_normalize 等)
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）上記はソース一部抜粋に基づく構成です。実際のファイル群はリポジトリの src/kabusys 配下を参照してください。

重要な実装上のメモ
-----------------
- run_execution:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。本番 DB と完全分離されています。
  - 起動直後にプロセス優先度を "high" に変更しようとします（psutil を使用）。
- run_monitoring:
  - 監視ループは MONITOR_POLL_INTERVAL（秒、default 60）で実行されます。0 以下や不正な値はデフォルトにフォールバックされます。
  - 監視は常に settings.sqlite_path（monitoring.db）を使用します（env にかかわらず本番監視 DB を使用する設計）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブルと必要なカラムを冗長に作成・マイグレーションします（冪等）。
- AI モジュール:
  - OpenAI API を使う処理は API 呼び出し失敗時にフェイルセーフ（0 またはスキップ）で継続する設計。
  - レスポンスのバリデーションやリトライロジック（指数バックオフ）を実装。

よくある運用手順（例）
- 初回セットアップ:
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config --strict
- 開発環境でペーパートレードを試す:
  1. KABUSYS_ENV=paper_trading を .env に設定
  2. python -m kabusys.run_execution
  3. python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- 監視を常時起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

サポート / 貢献
----------------
- .env に API キー等の機密情報が含まれます。これらは絶対に公開リポジトリへコミットしないでください。  
- 追加の設定ファイルは config/*.yaml（テンプレートは scripts/generate_config.py 等で生成可能）を利用します。  
- バグ報告・プルリクエストはリポジトリの Issue / PR をご利用ください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）。

最後に
------
この README はソースコード注釈と CLI の使い方を簡潔にまとめたものです。実運用前には必ず python -m kabusys.validate_config を実行して設定を確認してください。必要に応じて logs/ と data/ のパーミッションやバックアップ、OpenAI API の利用制限に関する運用ルールを整備してください。