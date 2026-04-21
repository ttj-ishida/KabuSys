README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下を含みます。
- 発注・実行エンジン（ExecutionEngine）
- 監視コンポーネント（Monitoring）
- ポートフォリオ構築・リスク制御の純粋関数群（portfolio）
- ファクター計算・リサーチ用ユーティリティ（research）
- ニュース NLP / レジーム判定（OpenAI を用いた AI モジュール）
- 運用支援スクリプト（環境設定ウィザード、設定検証、レポート生成 等）

主な設計方針
- 本番/ペーパートレード環境の分離（paper_trading 時は専用 SQLite を使用）
- .env による設定管理（自動ロード機能あり）
- DuckDB を分析用 DB、SQLite を監視・注文ログ用 DB に使用
- OpenAI（gpt-4o-mini）をニュース解析・レジーム判定で使用（任意）

主な機能一覧
----------------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成/更新
- 設定検証: python -m kabusys.validate_config で環境変数・config/*.yaml をチェック
- ExecutionEngine 起動: python -m kabusys.run_execution（KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動: python -m kabusys.run_monitoring（監視ループ、MONITOR_POLL_INTERVAL で間隔指定可）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算（momentum, volatility, value）と研究ユーティリティ（IC, forward returns）
- ニュース NLP スコアリング（OpenAI 必須）: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（OpenAI 必須）: kabusys.ai.regime_detector.score_regime
- 監視 DB 層（monitoring_db）: system_status / trade_logs / positions / risk_logs / dashboard の管理
- Kill Switch: リスク条件で data/kill.flag を書き込み ExecutionEngine を停止可能

セットアップ手順
----------------
1. クローン & 作業ディレクトリ
   - リポジトリをクローンし、プロジェクトルート（pyproject.toml または .git を含む）に移動します。

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml（config/*.yaml の検証をする場合に任意）
   - 例: pip install duckdb psutil openai pyyaml

4. .env の作成
   - python -m kabusys.config_setup を実行して対話的に .env を作成します。
   - あるいは .env.example を参考に手動で作成してください（.env は絶対に Git にコミットしないでください）。

5. 設定検証（必須）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリ / ログディレクトリ
   - デフォルトでは data/ や logs/ にファイルを作成します。適宜パスを .env で変更してください。
   - デフォルトパス例:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_DIR=logs
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

使い方
------
一般的な起動フロー例:

1. 監視（Monitoring）を起動
   - 環境変数でポーリング間隔を上書き可能:
     - MONITOR_POLL_INTERVAL=30（秒）
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - run_monitoring は常に本番用の sqlite_path（settings.sqlite_path）を使用します。
     - プロセス優先度を高に設定し、監視データを SQLite に書き込みます。

2. 実行エンジン（ExecutionEngine）を起動
   - KABUSYS_ENV によって挙動が変わります:
     - development: 発注なし（開発用）
     - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
     - live: 実際にブローカーへ発注
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - 外部から停止を指示するにはプロジェクトルート/data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了します。
     - またリスクトリガーにより data/kill.flag が書き込まれると ExecutionEngine は停止します（設定による）。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. OpenAI を使う機能
   - ニュース NLP（score_news）やレジーム判定（score_regime）は OPENAI_API_KEY 環境変数が必要です。
   - 例: export OPENAI_API_KEY="sk-..."（Linux/macOS）

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- LOG_DIR（デフォルト: logs）
- OPENAI_API_KEY（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）

運用メモ
- run_monitoring と run_execution はそれぞれプロセス優先度を "high" に設定します（utils.process_priority）。
- ログは stdout と logs/<app_name>.log に日次ローテートで出力されます（TimedRotatingFileHandler）。
- 監視ロジックは monitoring_db.init_monitoring_db により必要テーブルを自動作成・マイグレーションします。
- Kill Switch（data/kill.flag）は一度書き込まれると存在する限り実行エンジンの起動を阻止します。KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアする挙動がありますが、本番では 0 を推奨します。
- ペーパートレードは本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py                 -- パッケージ定義・バージョン
    config.py                   -- 環境変数/.env 自動ロードと Settings クラス
    config_setup.py             -- .env 対話ウィザード
    validate_config.py          -- 設定検証 CLI
    run_execution.py            -- ExecutionEngine 起動スクリプト
    run_monitoring.py           -- Monitoring 起動スクリプト
    tools/
      paper_verification_report.py -- Paper Trading 検証レポート生成
    ai/
      news_nlp.py               -- ニュース NLP スコアリング（OpenAI）
      regime_detector.py        -- 市場レジーム判定（OpenAI）
    monitoring/
      monitoring_db.py          -- SQLite 監視 DB 層
      system_monitor.py         -- システム・データ鮮度監視
      trade_monitor.py          -- 注文・約定監視（存在）
      risk_monitor.py           -- ドローダウン・ポジション上限監視
      kill_switch.py            -- Kill Switch 制御
      monitoring_engine.py      -- 各 Monitor を束ねるエンジン
      alert_manager.py          -- アラート送信ラッパー（存在）
    execution/
      (Execution エンジン周りの実装: broker_factory, execution_engine, order_manager, risk_manager, reconciler, order_repository 等)
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    data/
      (data pipeline / stats 等のユーティリティ。DuckDB を参照するモジュール群)
    utils/
      logging_setup.py          -- ログ設定ユーティリティ
      process_priority.py       -- プロセス優先度/CPU affinity 設定
      (その他汎用ユーティリティ)

補足ドキュメント / 参考
- PortfolioConstruction.md / StrategyModel.md（リポジトリに含まれる場合、ポートフォリオ・戦略の詳細設計が記載されています）
- config/*.yaml: system_config.yaml 等（generate_config.py で生成可能）

ライセンス / 注意事項
- .env に API キーやシークレットを含めるため、.env は絶対にバージョン管理にコミットしないでください。
- live 環境での運用はリスクが伴います。KABUSYS_ENV=live の設定は十分に注意して行ってください（validate_config は本番向けの追加警告を出します）。
- OpenAI API 利用時の料金・利用規約に注意してください。

問題報告 / 開発
- バグや改善提案は Issues を通じて報告してください。
- 変更を行う際はユニットテストと設定検証を実行の上、慎重にマージしてください。

以上。必要なら README に含めるサンプル .env テンプレートや起動シナリオ（systemd ユニット例、Dockerfile 例）も追加できます。希望があれば追記します。