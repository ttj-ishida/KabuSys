KabuSys — 日本株自動売買システム
=================================

本ドキュメントはこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
----------------
KabuSys は日本株の自動売買／研究を支援する小規模なフレームワークです。  
主な目的は以下を含みます。

- 発注エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- ファクター算出・リサーチ用ユーティリティ（DuckDB を利用）
- Paper Trading (模擬発注) をサポート
- ニュースを用いた NLP（OpenAI）によるスコアリング / レジーム判定
- 監視・アラート・Kill Switch による運用保護メカニズム

主な機能一覧
-------------
- 環境設定管理（.env 自動読込 / Settings ラッパ）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて paper_trading（MockBroker）と本番を分離
  - PID ファイル管理、停止フラグ対応
- Monitoring（run_monitoring / MonitoringEngine）
  - システム状態、注文滞留や約定異常、リスク（ドローダウン・ポジション上限）の定期チェック
  - Kill Switch による実行エンジン停止トリガー
- MonitoringDB（SQLite） によるログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ（候補選定、等/スコア重み、ポジション決定、セクター上限、レジーム乗数）
- Research モジュール（DuckDB を使ったファクター計算・IC計算・将来リターン等）
- AI モジュール（OpenAI を利用したニュースセンチメント、レジーム判定）

セットアップ手順（ローカル開発向け）
-------------------------------
1. リポジトリをクローン
   - 例: git clone <repo> && cd <repo>

2. Python 環境準備
   - 推奨: 仮想環境を作成してアクティベート
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージインストール
   - pip install -e .    # パッケージ配下を編集可能インストール（プロジェクトルートに pyproject.toml 等がある前提）
   - 追加依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. 環境変数設定（.env を作成）
   - コマンドで対話的に作成: python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 便利な設定（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE（instant|partial|never|reject）
   - 自動ロード:
     - パッケージ起動時にプロジェクトルートの .env, .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

6. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

起動・使い方
------------

基本的な実行コマンド（モジュールとして実行）

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid（デフォルト）へ PID を書き、停止フラグ（data/stop_requested.flag）が存在すれば起動せず終了します。
    - 停止は stop flag（data/stop_requested.flag）作成で行えます。

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL を使ってポーリング間隔を上書き可能（秒、デフォルト 60）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 動作:
    - 監視は MonitoringDB（Settings.sqlite_path、監視用 DB）にログを書きます。監視は本番 sqlite_path を常に使用します（環境にかかわらず）。
    - stop flag（data/stop_requested.flag）を検知するとループを終了します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で db パスを指定可能。出力は標準出力にテキストレポート。

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック、paper_trading DB を使用
  - live: 本番（実際に発注）
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API を使う AI 機能で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_*: Kill Switch / 起動時の挙動に関する設定（例: KILL_FLAG_CLEAR_ON_START）

停止・制御（実運用で重要）
------------------------
- 停止フラグ:
  - data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を監視し、検出時にループやスレッドを終了します（運用上の緊急停止）。
- Kill Switch:
  - KillSwitch は監視ルール（ドローダウン超過、ポジション上限超過等）に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側は kill.flag を検査して停止する実装を期待します。
- PID ファイル:
  - data/execution.pid（デフォルト）に起動中の ExecutionEngine の PID を書きます。SystemMonitor は PID ファイルの存在/有効性もチェックします。

開発者向け API / モジュール（簡易説明）
-----------------------------------
- kabusys.config: 環境変数読み込み・Settings ラッパ（.env 自動ロードロジック含む）
- kabusys.config_setup: 対話式 .env 作成ウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.execution: 発注関連（BrokerFactory、ExecutionEngine、OrderManager、Reconciler、RiskManager 等）
- kabusys.monitoring: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / MonitoringDB
- kabusys.portfolio: ポートフォリオ候補選定・重み算出・ポジションサイジング・セクター制限・レジーム乗数
- kabusys.research: DuckDB を使ったファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- kabusys.ai: news_nlp（ニュースセンチメント→ai_scores）、regime_detector（市場レジーム判定）
- kabusys.tools.paper_verification_report: Paper Trading の検証レポート出力

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下を抜粋）

- __init__.py
- config.py                    — 環境変数 / Settings
- config_setup.py              — .env 対話ウィザード
- validate_config.py           — 起動前検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - order_record.py

- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py

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

- utils/
  - process_priority.py

運用上の注意（簡潔）
-------------------
- 本番（KABUSYS_ENV=live）での運用前に必ず validate_config で設定を確認してください。
- .env は機密情報を含むため Git へ絶対にコミットしないでください。
- AI 機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しは失敗時にフォールバックする実装が多いですが、API 利用ポリシーや料金には注意してください。
- paper_trading モードは本番 DB と完全分離されるよう設計されていますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH の確認）。
- process priority / CPU affinity の設定は psutil に依存し、権限不足などで設定に失敗することがあります（ログに警告）。

トラブルシューティング
---------------------
- .env が読み込まれない / 値が反映されない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認。プロジェクトルートに .env/.env.local があるか確認。
- DB 周りのエラー:
  - data ディレクトリのパーミッションとファイルパス（DUCKDB_PATH / SQLITE_PATH）を確認してください。
- OpenAI 呼び出しの失敗:
  - OPENAI_API_KEY が正しく設定されているか、ネットワーク接続、rate limit を確認してください。実装側はリトライやフォールバックを用意しています。

ライセンス・貢献
---------------
- 本 README はコードベースから自動生成した説明です。実際のライセンス・コントリビュート手順はリポジトリのトップレベルの LICENSE や CONTRIBUTING を参照してください。

この README に記載のコマンドやパスはリポジトリ内の実装（src/kabusys/*.py）に基づいています。追加の操作や詳細な実装理解が必要な場合は各モジュールのドキュメント文字列（docstring）とソースコードをご参照ください。