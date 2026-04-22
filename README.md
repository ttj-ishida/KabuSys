KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買システム（KabuSys）のコアモジュール群を含みます。
主な機能はシグナル生成・ポートフォリオ構築・発注エンジン・監視・レポート生成・AI ベースのニュース評価などです。

注意
----
- .env（APIキー等を含む）を必ず設定してください。`.env` は絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では設定を慎重に行ってください（validate_config の警告を参照）。

主な特徴
---------
- 実行モード切替（development / paper_trading / live）
  - paper_trading モードは MockBroker を使い、発注ログは専用の paper_trading DB に記録して本番 DB と分離
- ExecutionEngine（発注）と Monitoring（監視）をプロセスとして起動可能
- Kill Switch / stop フラグを用いた安全停止機構
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）モジュール
- OpenAI（gpt-4o-mini）を用いたニュースNLP と市場レジーム判定（APIキー必須）
- ペーパートレード検証レポートの生成ツール
- .env を対話形式で作成するウィザードと起動前検証 CLI

機能一覧
---------
- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV により broker を切替）
  - run_monitoring.py: SystemMonitor を周期実行する監視プロセス起動スクリプト
- 設定管理
  - config_setup.py: .env の対話式ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI（--strict オプションあり）
  - config.py: Settings クラス（環境変数参照）と自動 .env ロードロジック
- 監視（monitoring）
  - monitoring_db.py: SQLite を使った監視ログ永続化
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager 等
- ポートフォリオ構築（portfolio）
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py など（純粋関数・DB 非依存）
- リサーチ（research）
  - factor_research.py: モメンタム・バリュー・ボラティリティ等の計算（DuckDB）
  - feature_exploration.py: 将来リターン計算・IC 計算・統計サマリー
- AI（ai）
  - news_nlp.py: ニュース記事を集約して OpenAI へ送りセンチメントを ai_scores に書き込み
  - regime_detector.py: ETF 指標 + マクロニュースを LLM で評価して market_regime を書込み
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成（期間指定可）
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. Python 環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（代表例）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を有効にするには: pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで data/ 以下に DB や PID・flag ファイルが作られます。必要に応じて権限やディレクトリ構成を確認してください。

環境変数（主なもの）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

重要（推奨）:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db） — KABUSYS_ENV=paper_trading 時に使用
- OPENAI_API_KEY: OpenAI を利用する機能で必要（news_nlp, regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

実行時オプション・挙動
--------------------
- run_monitoring.py
  - 起動: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず監視 DB は production path を参照）

- run_execution.py
  - 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
  - 実行中は data/stop_requested.flag の存在検知で安全にシャットダウン
  - PID ファイル: data/execution.pid（デフォルト）

- Kill / Stop の制御
  - KillSwitch はルールに応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます（Settings.kill_flag_path）
  - 手動で実行を止めたい場合:
    - Execution を止める: touch data/stop_requested.flag（run_execution, run_monitoring が検知して終了）
    - Kill を要求する（ExecutionEngine 側で検出されると発注停止等）： touch data/kill.flag

- Paper trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

使い方（コマンド例）
-------------------
- .env を作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- 手動停止（即時終了フラグ）
  - touch data/stop_requested.flag

- Kill Switch を外部から動かす（監視ロジックにより自動作成されることが多い）
  - echo "reason" > data/kill.flag

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定: --db path/to/paper_trading.db

AI 関連
-------
- news_nlp.score_news と regime_detector.score_regime は OpenAI API にアクセスします。API キーは OPENAI_API_KEY 環境変数か関数引数で指定してください。
- 大量リクエスト・429・5xx は内部でリトライ・バックオフ処理がありますが、API 利用制限・コストには注意してください。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で統一して行われます。
- デフォルトログディレクトリ: logs/
- 各アプリケーションは <log_dir>/<app_name>.log に日次ローテーションで出力します（30日分保持）。

ディレクトリ構成
----------------
以下はソースツリー（src/kabusys）に含まれる主なファイルとディレクトリの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings クラス
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証ツール
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングスクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - alert_manager.py (等)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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

運用上の注意
-------------
- KABUSYS_ENV=live のときは LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch 設定を必ず確認してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB（sqlite_path）を常に参照します。paper_trading の発注ログとは分離されています。

貢献
----
バグ報告・機能要望は Issue を作成してください。プルリクエストは歓迎します。

ライセンス
---------
（プロジェクトに合わせて記載してください）

-- End README --