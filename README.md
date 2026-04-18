KabuSys — 日本株自動売買システム
================================

本ドキュメントはリポジトリ内の主要スクリプト・モジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 周りのユーティリティ等）の概要、セットアップ、実行方法をまとめた README です。日本語で記載します。

プロジェクト概要
---------------
KabuSys は日本株自動売買システムの基盤ライブラリ／実行スクリプト群です。主な役割は次のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理を行いブローカと連携して注文を出す（本番 / ペーパートレードに対応）。
- Monitoring：システム稼働状況・データ鮮度・注文状態・リスク指標を継続監視し、必要に応じて Kill Switch を発動する。
- Portfolio construction：シグナルから候補選定、重み付け、株数算出（position sizing）を行う純粋関数群。
- Research：DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）。
- AI（ニュース NLP / レジーム判定）：OpenAI を利用したニュースセンチメントと市場レジーム判定。
- ユーティリティ：設定読み込み・.env ウィザード、設定検証、ログ設定、プロセス優先度制御など。

機能一覧
--------
主な機能（抜粋）：

- 実行エンジン（run_execution.py）
  - 本番（live）とペーパートレード（paper_trading）を切り替え可能
  - Paper Trading 時は MockBrokerClient を使用し、専用 SQLite に記録
  - PID / 停止フラグ管理、リスク管理、order_manager 等の組立て

- 監視（run_monitoring.py / monitoring パッケージ）
  - CPU/MEM/DISK、プロセス生存、データ鮮度のポーリング
  - TradeMonitor、RiskMonitor、KillSwitch、AlertManager と連携
  - MONITOR_POLL_INTERVAL によるポーリング間隔調整

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等重・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクター制限、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC（情報係数）、統計サマリ等

- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

- CLI ユーティリティ
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python 環境を作成（例）
   - python 3.10+ を推奨
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がある場合はそれを使用してください。ない場合、主に以下が必要です:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 初期設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE 等

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告があっても exit(1) になります。

5. 初期データディレクトリ作成（必要に応じて）
   - デフォルトで data/ 以下を利用します（例: data/kabusys.duckdb, data/monitoring.db）。
   - ログは logs/ 以下に出力されます（LOG_DIR で変更可）。

環境変数 / 設定（主要）
-----------------------
（ここでは主な変数のみを列挙）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - default: development

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（省略可, default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI モジュールを使う場合必須）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB default: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject, default: instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO）
- LOG_DIR（ログ出力ディレクトリ）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）, run_monitoring で参照。default: 60）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか。0/1。default: 0）
- PID_FILE_PATH / KILL_FLAG_PATH（デフォルトは data/execution.pid / data/kill.flag）

実行方法（代表的なコマンド）
-------------------------

- ExecutionEngine を起動（バックグラウンド実行等は OS の方法で行ってください）
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）に記録します。
    - 実行中は data/execution.pid を書き込み、 data/stop_requested.flag があると停止します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 概要:
    - Monitoring は常に（環境にかかわらず）本番 sqlite_path を使って監視ログを書きます（SQLITE_PATH）。
    - MONITOR_POLL_INTERVAL 環境変数で polling 間隔 (秒) を上書きできます（デフォルト 60 秒）。
    - 停止: data/stop_requested.flag を作成するとループが終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

停止 / Kill Switch 等
--------------------
- run_execution と run_monitoring はプロジェクトルートの data/stop_requested.flag をチェックして graceful shutdown します。停止したい場合はこのファイルを作成してください。
- Kill Switch: リスク判定で kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine 停止のための信号になります。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で行います。デフォルトは logs/<app_name>.log に日次ローテーションで保持（30日）します。LOG_DIR 環境変数で変更可能です。

開発者向け API（概要）
---------------------
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- kabusys.ai
  - score_news（AI によるニューススコアリング）
  - regime_detector.score_regime（市場レジーム判定）

- kabusys.monitoring
  - MonitoringDB、SystemMonitor、RiskMonitor、TradeMonitor、KillSwitch、MonitoringEngine 等

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリの主要なモジュール配置（src/kabusys 配下）抜粋です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (省略されているが存在想定)
    - alert_manager.py (同上)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/
    - execution_engine.py (実行エンジン本体)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (実行時に使用)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag

注意事項 / 運用上のポイント
--------------------------
- 本番環境（KABUSYS_ENV=live）では設定値を慎重に確認してください（validate_config は推奨）。
- .env は機密情報を含むため絶対に Git 等にコミットしないでください。
- run_monitoring は監視専用 DB（SQLITE_PATH）に書き込みます。monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは環境に依存しない）。
- psutil によるプロセス優先度設定や CPU affinity は環境に依存します。権限不足で設定に失敗しても警告で継続します。
- OpenAI の呼び出しは失敗耐性（リトライ、フェイルセーフ）を備えていますが API キー・レート制限には注意してください。
- DuckDB への書き込みは一部の executemany 動作に注意（モジュール内で互換性確保処理あり）。

よくある操作例
--------------
- .env を作成して設定検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレードで Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視を常駐させる（ポーリング間隔 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足（依存関係）
----------------
- 最低限必要なライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル YAML 検証用: 任意）

ライセンスや貢献方法などは本 README に含めていません。必要に応じて追記してください。

以上。必要があれば各モジュールの詳細なドキュメント（関数シグネチャ・戻り値や例外仕様）を別途作成します。