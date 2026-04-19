KabuSys — 日本株自動売買システム
=============================

本プロジェクトは日本株向けの自動売買システムのコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AIベースのニュース評価など）を提供します。本 README はコードベースから抽出した利用者向けドキュメントです。

主な特徴
-------
- 実行エンジン（ExecutionEngine）の起動スクリプト（発注処理・注文管理・リスク管理などを統合）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート / Kill Switch 機能
- ポートフォリオ構築とポジションサイジング（等金額・スコア加重・リスクベース）
- ファクター計算 / 研究用ユーティリティ（モメンタム・バリュー・ボラティリティ・IC 等）
- ニュースを LLM（OpenAI）でセンチメント評価してテーブルへ保存する機能
- Paper Trading モード（本番 DB と分離された専用 SQLite への記録）
- 各種 CLI ツール：環境設定ウィザード、設定検証、Paper Trading 検証レポート生成
- 統一的なログ設定（console + 日次ローテートファイル）・プロセス優先度設定・CPU affinity ユーティリティ

動作前提（推奨）
---------------
- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の構文検証をする場合に推奨）
- 環境変数により設定（.env ファイルをプロジェクトルートに置くことを想定）

必須環境変数（最低）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

その他の重要な環境変数（代表例）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading モード時に使用、デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

セットアップ手順
---------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - Python 仮想環境を作成・有効化
2. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai
   - （開発用に）pip install -r requirements-dev.txt が存在すれば参照
3. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成（.env は Git 管理下に置かないこと）
4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます: python -m kabusys.validate_config --strict
5. データディレクトリの用意
   - デフォルトでは data/ に DB・フラグ・pid ファイルが置かれます。コードは起動時に親ディレクトリを作成する場合がありますが、権限等に注意してください。
6. （AI 機能を使う場合）OPENAI_API_KEY を .env に設定

起動・使い方
-----------

スクリプトとしての起動は各モジュールをモジュール実行します。プロジェクトルートで以下を実行してください。

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全に分離）。
  - 停止方法:
    - run_execution は data/stop_requested.flag の存在を確認し終了します（手動でファイル作成して停止させる運用も可能）。
    - また Kill Switch（監視コンポーネント）が基準を満たすと data/kill.flag を書き込み、Engine に停止シグナルを送ります（Engine 側で kill.flag を検出すると停止します）。
  - PID ファイル:
    - data/execution.pid（デフォルト）に PID を書きます。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は MonitoringDB（SQLite）を使い system_status / trade_logs / risk_logs / positions / dashboard を管理します。
  - 停止方法:
    - プロジェクトルート data/stop_requested.flag を作成するとループを抜けます。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話形式で作成・更新します。

- 設定検証 CLI
  - python -m kabusys.validate_config
  - config/*.yaml や主要環境変数の検証を行います。PyYAML がインストールされていれば YAML のパースも確認します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数がなければデフォルト data/paper_trading.db）

ログ設定
--------
- 共通ユーティリティでログは標準出力と日次ローテートファイルへ出力します。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名ごと（例: logs/execution.log, logs/monitoring.log）
- 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

監視・Kill Switch・フラグファイル
-------------------------------
- stop_requested.flag: run_execution / run_monitoring がチェックする停止フラグ（shutdown シグナル運用向け）
  - path: プロジェクトルート/data/stop_requested.flag
- kill.flag: KillSwitch が作成するフラグ（実行エンジンを強制停止するための論理フラグ）
  - path は Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch はリスクアラート（ドローダウン超過やポジション上限超過）を検出した場合にこのファイルを書き、ExecutionEngine に停止シグナルを送ります。
- PID ファイル:
  - data/execution.pid（ExecutionEngine 起動で使用）

主要モジュール / 機能一覧
-----------------------
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.run_monitoring — SystemMonitor ポーリングループ起動スクリプト
- kabusys.config / kabusys.config_setup — 環境変数管理・ウィザード
- kabusys.validate_config — 起動前チェック CLI
- kabusys.monitoring —
  - monitoring_db — SQLite 永続層
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager
- kabusys.execution — 発注関連コンポーネント（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager）
- kabusys.portfolio — ポートフォリオ構築（候補選定・重み計算・セクター制約・ポジション決定）
- kabusys.research — ファクター計算、特徴量探索、IC 計算等
- kabusys.ai — AI 関連（news_nlp: ニュースセンチメント評価、regime_detector: 市場レジーム判定）
- kabusys.tools — 補助ツール（paper_verification_report など）
- kabusys.utils —
  - logging_setup — ログ設定ユーティリティ
  - process_priority — プロセス優先度 / CPU affinity 設定

ディレクトリ構成（抜粋）
----------------------
プロジェクトルート（src/kabusys をインポートできる状態を想定）:

- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - monitoring/ (上に重複、実際は同ディレクトリ)
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/ (ランタイムで使用するファイル)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb (デフォルト)
      - execution.pid
      - kill.flag
      - stop_requested.flag
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （テンプレート／生成スクリプトを用意してある想定）

サンプル .env（最小）
-------------------
以下は参考例（実運用では .env を絶対にリポジトリにコミットしないでください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0（クリアしない）を推奨します。
- paper_trading モードは実発注を行いませんが、発注ロジックの検証に便利です。本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI など外部 API を利用する箇所はネットワーク遅延や API 障害を想定した冗長化（リトライ・フェイルセーフ）が組み込まれていますが、API キーやコスト管理には注意してください。
- ログ・DB のパスや Perlmission（権限）によりファイル作成が失敗する場合、ログファイルが生成されずコンソール出力のみになる場合があります。権限を確認してください。

開発・テスト
-------------
- モジュール単位の関数群は純粋関数として設計されている箇所が多く（portfolio, research など）、ユニットテストが書きやすくなっています。
- OpenAI 呼び出し等は内部でラップされているため、ユニットテストでは呼び出し関数をモックして動作確認が可能です（コード内に patch で差し替えられる旨の注記あり）。

さらに詳しい情報
----------------
- 各モジュールの docstring に設計意図・注意点・使用例が詳述されています。実装や挙動を確認する際は該当ファイルを参照してください。
- config/*.yaml は動作設定を記述するために用意されています。生成スクリプトやテンプレートが同梱されている想定です。

問題報告 / コントリビューション
------------------------------
README を参照しても不明点がある場合は、issue を作成してください。設計方針に関する議論やテスト追加の PR は歓迎します。

以上。