KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群です。  
本 README はコードベースから抽出した主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は下記の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注（実注文 / ペーパートレード）の実行を担うエンジン
- Monitoring：システム稼働状況・発注状態・リスク制御の定期監視
- Portfolio construction：候補選定、重み付け、株数計算、セクター制限、レジーム調整
- Research：DuckDB 上の価格・財務データからファクター計算・特徴量解析
- AI 補助：ニュースの NLP によるセンチメント算出、マクロセンチメントを用いた市場レジーム判定
- ユーティリティ：ロギング設定、プロセス優先度制御、設定ファイル (.env) ウィザード、設定検証 CLI
- ツール：Paper Trading の検証レポート生成など

主な特徴
--------
- 環境分離
  - KABUSYS_ENV により development / paper_trading / live の振る舞いを切替
  - paper_trading では専用の SQLite DB（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離
- 監視機能
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセスの生存チェック
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウンやポジション数の監視
  - KillSwitch：所定条件で data/kill.flag を書き込み ExecutionEngine を安全に停止
  - monitoring.db（SQLite）への永続化
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重/スコア重み、リスクベースの株数決定、セクターキャップ、レジーム乗数
- 研究用機能
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、統計サマリ
- AI 統合
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計（ai/news_nlp.py）
  - マクロニュース + ETF MA200 を合成したレジーム判定（ai/regime_detector.py）
  - API 呼び出しはリトライ、レスポンス検証、フェイルセーフ実装
- ロギング
  - 統一的な setup_logging を提供。コンソール（stdout）と日次ローテートファイル出力（logs/*.log）

セットアップ手順
----------------

1. リポジトリを取得・仮想環境作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須（概ね以下を想定）
     - duckdb
     - psutil
     - openai
   - Optional
     - PyYAML（設定ファイル検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成される主な環境変数（.env.example を参照）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL / LOG_DIR 等
   - 自動ロード: config.py がプロジェクトルートを検出すると .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります。

5. データディレクトリ作成
   - 必要に応じて data/ や logs/ を作成します（logging_setup が自動作成する場合があります）。

使い方（実行例）
----------------

- 監視プロセスの起動（ポーリングループ）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 停止は Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成すると検出して終了します。

- 実行エンジン（ExecutionEngine）の起動
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading DB に記録されます（本番 DB と分離）。
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID が書かれます。

- .env の作成/更新ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能、環境変数 PAPER_TRADING_SQLITE_PATH 優先度あり。

- AI モジュール（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定してください。
  - 例（ニューススコア、外部呼び出し例）:
    - Python から: from kabusys.ai.news_nlp import score_news
    - DuckDB 接続を渡して利用する設計です（score_news(conn, target_date, api_key=None)）。

主要環境変数のまとめ
--------------------
- KABUSYS_ENV: development | paper_trading | live（動作モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- setup_logging(app_name="execution" など) で統一的に設定されます。
- コンソール出力は stdout を使用します。

停止・Kill Switch
----------------
- KillSwitch は監視がトリガー条件を満たすと data/kill.flag を作成します。ExecutionEngine はこのフラグを検出して停止できます。
- 手動停止には data/stop_requested.flag を作成することで run_monitoring/run_execution のループを終了させることができます。

ディレクトリ構成（主要ファイル）
--------------------------------
概要は src/kabusys 以下の主要モジュール中心に示します。

- src/kabusys/
  - __init__.py (バージョン定義)
  - config.py (設定 / .env 自動ロード、Settings)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - utils/
    - logging_setup.py (ロギング設定)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py (滞留注文等の監視モジュール)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py (複数モニタの統合)
    - alert_manager.py (アラート送信管理)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py (Mock / 実クライアントの切替)
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (データ格納ディレクトリ、実行時にファイルが作られる)
  - tools/
    - paper_verification_report.py

設計上の注意点 / 開発者向けメモ
------------------------------
- 設定は基本的に環境変数経由。config.py はリポジトリルートの .env / .env.local を自動読み込みします（必要に応じて無効化可能）。
- paper_trading モードでは本番の発注ロジックに影響を与えないよう DB とブローカークライアントを分離しています。
- AI 呼び出しは外部 API に依存するため、テスト時は呼び出し関数をモックする設計になっています（_call_openai_api のパッチ等）。
- DuckDB を使う研究系コードは接続オブジェクトを受け取り SQL と Python で完結するように設計されています（本番口座や発注 API にはアクセスしません）。
- ロギング/プロセス優先度設定は全起動スクリプトから呼び出して統一しています。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください。リポジトリ固有の情報があれば追記をお願いします。）

補足
----
この README は提供されたコードベースの主要な構成と使い方をまとめたものです。実運用にあたっては .env.example の確認、validate_config による検証、バックアップや安全停止手順の整備を必ず行ってください。質問や補足の説明が必要であればお知らせください。