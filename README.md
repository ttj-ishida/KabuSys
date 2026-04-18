README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の簡易実装です。  
主な目的は以下です。

- データ基盤（DuckDB を用いたファクター計算／リサーチ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 実行エンジン（発注ロジック・リスク管理・Order 管理）
- 監視基盤（プロセス・システム状態・注文状態の監視、Kill Switch）
- AI 連携（ニュースのセンチメント評価、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

上記はモジュール化され、ローカル／ペーパートレード／本番を区別して動作します。

主な機能一覧
-------------
- 環境設定管理
  - .env の自動読み込み（.env.local を上書き可能）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応
- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - システム負荷・データ鮮度・プロセス存否を定期ポーリングして SQLite に記録
  - Kill Switch による ExecutionEngine 停止（data/kill.flag）
  - MONITOR_POLL_INTERVAL によるポーリング間隔制御（デフォルト 60 秒）
- モジュール群
  - portfolio: 銘柄選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
  - research: ファクター計算（Momentum / Volatility / Value）、特徴量探索、IC 計算
  - ai: ニュース NLP（OpenAI でセンチメント）・レジーム判定（MA + マクロセンチメント）
- 監視 DB 層
  - monitoring_db: system_status, trade_logs, positions, risk_logs, dashboard を管理
- 開発 / 運用ツール
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合、少なくとも次をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML (設定検証で YAML 検証を行う場合)
   例:
     - pip install duckdb psutil openai PyYAML

4. 初期設定（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - 任意: OPENAI_API_KEY（AI 機能を使う場合）
   - 主な環境変数（デフォルト値）:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0（1 にすると起動時に kill.flag を自動クリア）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

使い方（起動・運用）
-------------------

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録されます
  - 停止フラグ: data/stop_requested.flag が置かれると起動を中止または実行中に停止要求を送れます
  - Kill Switch:
    - 監視側が条件を満たすと data/kill.flag を作成します。ExecutionEngine はこれを検出して停止します
    - kill.flag を削除するには手動でファイルを削除してください（危険なので本番では注意）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: env または data/paper_trading.db を参照

主な環境変数（抜粋）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live

- DB/ファイル:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用, default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)

- ロギング:
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)

- Paper Trading 固有:
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)

- 監視:
  - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）

停止・プロセス制御
------------------
- run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を監視します。停止したいときはこのファイルを作成してください。
- 監視モジュールは条件により data/kill.flag を書き込み、ExecutionEngine に停止を促します（Kill Switch）。
- PID ファイル（data/execution.pid）を用いて外部からプロセス管理を行います。

ディレクトリ構成 (主要ファイル)
-----------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の読み込みと Settings クラス
  - config_setup.py
    - .env を対話式に生成するウィザード
  - validate_config.py
    - .env と config/*.yaml の検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite への永続化層（テーブル作成・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文状態監視: ファイル中に実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタをまとめてポーリング
    - kill_switch.py — Kill Switch 実装（kill.flag 操作）
    - alert_manager.py — 通知管理（LINE などへ通知する想定）
  - execution/
    - execution_engine.py — 実行エンジン（発注ループ）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注・リスク管理・ブローカ抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算（リスクベース / 等配分）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント評価（ai_scores 書込み）
    - regime_detector.py — MA200 + マクロセンチメントで市場レジーム判定
  - data/  (実行時に使用するディレクトリ、リポジトリ外)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid / stop_requested.flag / kill.flag
  - logs/ (デフォルトのログ出力先、LOG_DIR で変更可能)

注意事項 / 運用上のヒント
------------------------
- 本番での KABUSYS_ENV=live 設定は慎重に行ってください。validate_config はいくつかの本番向け警告を出します。
- kill.flag や stop_requested.flag の自動クリア設定は危険です（特に本番では KILL_FLAG_CLEAR_ON_START=0 を推奨）。
- OpenAI を用いる AI 機能は API コストとレイテンシに注意してください。OPENAI_API_KEY を環境変数で設定します。
- データベースファイル（DuckDB / SQLite）はデフォルトで data/ 以下に作成されます。バックアップや配置先は必要に応じて変更してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR で出力先を変更できます。

タグライン
--------
KabuSys は研究 → シグナル → 実行 → 監視まで一貫したワークフローを想定した軽量な自動売買基盤です。  
ローカル開発・ペーパートレードから本番運用まで段階的に利用できるよう設計されています。

必要があれば、README の英語版や各モジュールの使用例・API ドキュメント（関数シグネチャ例）を追加できます。どの部分を詳しく書くか教えてください。