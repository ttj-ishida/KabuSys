README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。
主な機能として、注文実行エンジン（ExecutionEngine）、システム監視（Monitoring）、
ファクター計算 / 研究用ユーティリティ、LLM を用いたニュースセンチメント評価などを含みます。

このリポジトリはライブラリ群と、起動用スクリプト（python -m で実行可能なモジュール）を提供します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（モックブローカー）/ live（実ブローカー）を切替え
  - ペーパートレード用にデータベースを完全分離 possible（data/paper_trading.db）
  - PIDファイル管理、停止フラグ（data/stop_requested.flag）による安全停止

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース・データ鮮度・注文ログの監視
  - Kill Switch（data/kill.flag）を用いた ExecutionEngine 停止トリガー
  - RiskMonitor（ドローダウン、ポジション上限検出） / TradeMonitor / SystemMonitor
  - アラート送信インターフェース（LINE 等を想定）

- 研究 / データ処理（research パッケージ）
  - ファクター計算（momentum, volatility, value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、重み計算、セクターキャップ適用、ポジションサイジング（lot 単位丸め等）

- AI モジュール（ai パッケージ）
  - news_nlp: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコアリング
  - regime_detector: MA200 とマクロセンチメントを合成して市場レジーム判定

- ユーティリティ
  - 設定ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
  - ログセットアップ、プロセス優先度設定ユーティリティ（utils）

前提（推奨）
-------------
- Python 3.9+（ソースは型ヒントを多用）
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML をパースする場合）
- SQLite3 は標準ライブラリで利用

（requirements.txt はリポジトリに含めていない場合があるため、適宜 pip install を実行してください）
例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  (Linux/macOS)
   .venv\Scripts\activate     (Windows)
3. 必要なパッケージをインストール
   pip install duckdb psutil openai PyYAML
4. 環境変数設定
   - 対話式ウィザードで .env を生成:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記を参照）
5. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - development, paper_trading, live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading の専用 SQLite、デフォルト: data/paper_trading.db)
- LOG_LEVEL (例: INFO, DEBUG)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト: 60)
- KILL_FLAG_CLEAR_ON_START (本番環境での Kill Switch 自動クリア防止、デフォルト: 0)

例: 最低限必要な .env（対話ウィザード利用を推奨）
  JQUANTS_REFRESH_TOKEN=xxxxxxxx
  KABU_API_PASSWORD=yyyyyyyy
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

起動方法（使い方）
-----------------

- ExecutionEngine を起動（デフォルトで Settings に従う）
  python -m kabusys.run_execution

  挙動の要点:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動直後に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - PID ファイルを data/execution.pid に書きます。

- Monitoring を起動
  python -m kabusys.run_monitoring

  挙動の要点:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - Monitoring は Settings にかかわらず本番 sqlite_path（SQLITE_PATH）を使って監視 DB を記録します。
  - 停止は data/stop_requested.flag を作成することで可能です。

- 設定ウィザード（.env を生成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（過去期間のサマリ）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照します。

AI 機能について
----------------
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を使用します。
  実行前に OPENAI_API_KEY を環境変数に設定してください。
- API 呼び出しはリトライやクリップ等の安全策が組み込まれていますが、
  APIキーの設定・コスト管理には注意してください。

ログ
----
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで出力されます（utils/logging_setup.py）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御可能。

停止 / Kill Switch / フラグファイル
----------------------------------
- 実行停止: data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して停止します。
- Kill Switch: リスク条件を満たした場合 monitoring 側が data/kill.flag を書き、Execution を停止させる仕組みがあります。
  - kill.flag を削除して再開する場合は手動でファイルを削除するか、KillSwitch.clear() を呼ぶ処理を使用してください。
- 注意: KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動でクリアします（本番では推奨しません）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py            — ニュースの LLM センチメント評価
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py      — システム監視
  - trade_monitor.py       — 注文監視（ログ差異検出等）
  - risk_monitor.py        — ドローダウン・ポジション制限監視
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 各モニタのオーケストレーション
  - alert_manager.py       — （アラート送信ラッパー: LINE 等に接続する実装想定）
- execution/
  - execution_engine.py    — ExecutionEngine（発注セッション制御）
  - broker_factory.py      — Broker クライアントの生成（Mock / 実装）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — 統一ロギング設定
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

注意事項・運用上のポイント
--------------------------
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 等の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を忘れずに。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。デフォルトは 0（クリアしない）。
- Monitoring は監視 DB（SQLITE_PATH）に書き込みを行います。重要データは適切なバックアップを検討してください。
- AI モジュール利用時は API レート・費用に注意してください。OPENAI_API_KEY は安全に管理してください。
- config/*.yaml（system_config.yaml 等）は .env と併せて各種設定を保持します。validate_config で存在・パース検証が可能です。

開発・テスト向けヒント
-----------------------
- 自動的な .env ロードを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからスクリプトをインポートしてください（テストで便利）。
- DuckDB や SQLite のテーブルスキーマはモジュール内の init 関数で自動作成・マイグレーションされる設計です（例: monitoring_db.init_monitoring_db）。
- LLM 呼び出し部分はテストしやすいように分離されており、テスト時は _call_openai_api などをモックできます。

サポート
-------
- この README はリポジトリ内のソースコードを元に作成しています。
- 実際の運用手順（systemd ユニット、コンテナ化、CI/CD など）は環境に合わせて追加してください。

以上。必要があれば「.env の具体的な例」「systemd ユニットの例」「Dockerfile / docker-compose のテンプレート」など、運用向けドキュメントを追補します。