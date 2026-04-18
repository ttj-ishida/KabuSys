KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株向け自動売買システム「KabuSys」の Python コードベースです。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

要約（プロジェクト概要）
--------------------
KabuSys は以下の責務を持つモジュール群で構成されています。

- データ処理・リサーチ（DuckDB を使ったファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム考慮）
- 実行エンジン（ExecutionEngine）および注文管理（ブローカークライアントの抽象化）
- 監視（System / Trade / Risk モニタ、Kill Switch、監視 DB の永続化）
- AI 補助（ニュース NLP によるセンチメント採点、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

主な機能一覧
-------------
- 環境設定ウィザード（.env の対話的作成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリングループ）: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 停止は data/stop_requested.flag によるフラグファイル
- 監視 DB（SQLite）永続化層: kabusys.monitoring.monitoring_db
  - system_status, trade_logs, positions, risk_logs, dashboard を管理
- 監視エンジン（MonitoringEngine）: System / Trade / Risk 各 Monitor を束ね、
  必要に応じて Kill Switch（data/kill.flag）を書き込む
- リサーチ用モジュール（DuckDB 経由）:
  - ファクター計算（momentum / volatility / value）: kabusys.research.factor_research
  - 特徴量探索・IC 計算等: kabusys.research.feature_exploration
- ポートフォリオ構築:
  - 候補選定・重み算出: kabusys.portfolio.portfolio_builder
  - ポジションサイズ計算（risk_based / equal / score）: kabusys.portfolio.position_sizing
  - セクター上限・レジーム乗数: kabusys.portfolio.risk_adjustment
- AI 補助:
  - ニュース NLP によるセンチメント (OpenAI)：kabusys.ai.news_nlp.score_news
  - マクロ + ETF MA を使った市場レジーム判定（OpenAI）：kabusys.ai.regime_detector.score_regime
- 開発補助ツール:
  - Paper Trading 検証レポート生成 CLI: kabusys.tools.paper_verification_report

前提・依存関係
--------------
最低限の実行環境（例）:
- Python 3.10+（typing の | と match を利用しているので 3.10 以上を想定）
- 必須パッケージ（pip install で導入）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config/*.yaml の検証に使用）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム差を吸収）

注: 実行には各種 API キー（J-Quants, kabuステーション, OpenAI など）が必要です。これらは .env に設定します（秘匿扱い、Git 管理しないこと）。

セットアップ手順
----------------

1. リポジトリをクローンし、Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （開発時）pip install PyYAML

3. .env の作成
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作り、必須環境変数を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他（KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）
   - 注意: .env は絶対にリポジトリにコミットしないでください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ / ログディレクトリの準備
   - デフォルトでは data/ および logs/ を使用します。起動スクリプトが自動作成する場合があります。

使い方（主要スクリプト）
------------------------

- ExecutionEngine 起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数により挙動が変わります:
    - development: 開発（発注なし）
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - live: 実際のブローカークライアントが使用されます（要設定）

  - 停止方法:
    - data/stop_requested.flag を作成すると起動中のループが検知して停止します。
    - また ExecutionEngine は設定された kill.flag (Settings.kill_flag_path) を監視し、発動時は発注を停止します。

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用（監視用 DB は本番 DB に保存されます）
  - 停止: data/stop_requested.flag を置くとループ終了

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD（期間指定）
    - --db PATH（SQLite ファイルパスの上書き）
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可能

- AI / リサーチ機能（ライブラリ呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を渡してリサーチ関数を呼ぶことを想定（例: kabusys.research.calc_momentum）

環境変数（主要）
----------------
主要な環境変数（.env に設定する）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- PAPER_FILL_MODE（paper_trading の fill 挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険 — デフォルト 0）

ログ・PID・フラグファイル
------------------------
- ログ: デフォルト logs/<app_name>.log（setup_logging により stdout + 日次ローテーションで出力）
- PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）
- 停止フラグ: data/stop_requested.flag（run_* スクリプトが監視）
- Kill Switch: data/kill.flag（KillSwitch が書き込む。ExecutionEngine はこれを検知して停止）

監視・DB の初期化
------------------
run_execution / run_monitoring は起動時に monitoring DB（SQLite）のテーブル作成を行います（init_monitoring_db）。  
既存 DB スキーマに対するマイグレーション（例: 列追加）も簡易的に行われます。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとして簡略化した一覧）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定取得ラッパ
  - config_setup.py — .env 対話ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py — 統一ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — monitoring DB 永続化層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py
    - trade_monitor.py (存在）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在）
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）上記は主要ファイルを抜粋したものです。細かい実装ファイルやテスト、追加ユーティリティはリポジトリ内に存在します。

実運用上の注意
---------------
- 本番（KABUSYS_ENV=live）では必ず .env の設定を厳重に確認してください（validate_config を推奨）。
- .env は機密情報（API キー・パスワード）を含むため、Git にコミットしないでください。
- Kill Switch（data/kill.flag）や stop_requested.flag を運用上うまく使うことで安全停止フローを実現しています。設定 KILL_FLAG_CLEAR_ON_START の取り扱いには注意してください（本番では 0 推奨）。
- OpenAI 等外部 API を利用する機能は API 使用料が発生するため、テスト時は呼び出し回数に注意してください。テストでは _call_openai_api をモックする設計になっています。

付録：よく使うコマンド例
----------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（デフォルト環境に従う）
  - python -m kabusys.run_execution

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

最後に
------
この README はソースコード内のドキュメント文字列（docstring）と設定ファイルの挙動に基づいて作成しています。詳細な運用・設計（例えば ExecutionEngine の内部や StrategyModel の仕様）は、対応する設計ドキュメント（Project 内の Markdown 等）を参照してください。必要であれば README に追記・改善しますので、補足してほしい箇所を教えてください。