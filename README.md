README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
主な目的は戦略の実行（ExecutionEngine）、システム監視（Monitoring）、ファクター計算やリサーチ、AI を使ったニュースセンチメントなどを統合することです。  
本リポジトリはモジュール単位で設計されており、ローカル開発・ペーパートレード・本番（live）の各実行モードをサポートします。

主な機能
--------
- ExecutionEngine（発注実行エンジン）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient をペーパートレードで利用）
  - リスク管理（position 上限、利用率、ドローダウン等）
  - 注文管理・リコンシリエーション

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク／プロセス生存／データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文状態やドローダウン監視
  - KillSwitch: リスクトリガーにより ExecutionEngine を停止する機構（data/kill.flag）
  - 監視結果の永続化（SQLite）

- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数

- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計要約

- AI / ニュース NLP
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（ai_scores）
  - 市場レジーム判定（ETF + マクロニュースの LLM 評価の合成）

- ユーティリティ
  - .env 対話型ウィザード（config_setup）
  - 起動前の設定検証ツール（validate_config）
  - Paper Trading 検証レポート生成ツール

セットアップ手順
---------------
1. Python と依存ライブラリ
   - Python 3.10+ を推奨
   - 必要なライブラリ例（プロジェクトの requirements.txt がある場合はそれを利用してください）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の構文チェックを行う場合に推奨）
   - 例:
     python -m pip install duckdb psutil openai PyYAML

2. リポジトリルートへ移動（.git または pyproject.toml を置くディレクトリがプロジェクトルートになります）

3. .env の作成（対話式ウィザード推奨）
   - 実行:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考にしてください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 実行時）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）

4. 設定検証（起動前チェック）
   - 実行:
     python -m kabusys.validate_config
   - 警告も FAIL として扱う strict モード:
     python -m kabusys.validate_config --strict

5. ログディレクトリ
   - デフォルト: logs/
   - 環境変数 LOG_DIR で変更可能
   - ログは日次ローテーションされ 30 日分保持されます（logs/<app_name>.log）

使い方
-----

基本的な起動コマンド（パッケージルートで実行）:

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
    - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します
    - 監視は常に「本番」SQLite パス（Settings.sqlite_path）を使用します（環境にかかわらず）

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、ペーパートレード専用 DB（data/paper_trading.db）に記録されます
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します
    - 実行中に停止させたい場合はプロジェクトルート/data/stop_requested.flag を作成してください
    - 実行中は PID ファイル（デフォルト data/execution.pid）にプロセス情報を書きます

- .env を対話式で作成/更新
  - python -m kabusys.config_setup

- 設定検証（起動前）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定できます

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定したうえで、アプリケーションコードから kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime を呼び出します。
  - これらは DB（DuckDB）接続を受け取り、ai_scores / market_regime テーブルを書き込みます。

プロセス制御・フラグファイル
--------------------------
- stop_requested.flag
  - run_monitoring / run_execution がポーリングして検知する停止フラグ（プロジェクトルート/data/stop_requested.flag）
  - ファイルを作ることで安全にシャットダウンできます

- kill.flag
  - KillSwitch が書き込むファイル（Settings.kill_flag_path, デフォルト data/kill.flag）
  - ExecutionEngine に対する緊急停止フラグ（ExecutionEngine はこのファイルの存在を監視している想定）

- PID ファイル
  - 実行エンジンは pid ファイル（デフォルト data/execution.pid）を使用します

設定（Settings）について
-----------------------
設定は kabusys.config.Settings クラス経由で環境変数から読み込まれます。主なプロパティ:
- jquants_refresh_token (必須)
- kabu_api_password (必須)
- kabu_api_base_url
- line_channel_access_token / line_user_id
- duckdb_path（デフォルト data/kabusys.duckdb）
- sqlite_path（デフォルト data/monitoring.db）
- paper_sqlite_path（デフォルト data/paper_trading.db）
- pid_file_path, kill_flag_path, kill_flag_clear_on_start
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL

ディレクトリ構成
----------------
（ソースルートは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／Settings 管理（自動 .env ロード機能付き）
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — データパイプライン / DB 関連モジュール（別ディレクトリ）
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック等)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py
  - research/                — DuckDB を使ったファクター計算等

補足・運用上の注意
-----------------
- データベース
  - DuckDB は分析用途（prices_daily、raw_financials、raw_news 等）に使用
  - SQLite は監視ログ／注文履歴等の永続化に使用（monitoring.db / paper_trading.db）

- ペーパートレード
  - KABUSYS_ENV=paper_trading にすると、MockBrokerClient が使用され、ペーパートレード専用 DB に記録されます。本番 DB と完全に分離されます。

- ロギング
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一的にログ出力します
  - 標準出力（stdout）へも出力されます。ログファイルは logs/<app_name>.log に日次ローテーションで保存されます

- AI（OpenAI）機能
  - OPENAI_API_KEY を必ず設定してください。API の失敗は多くの場合フォールバック（0.0 など）で安全に処理される設計ですが、レート制限やコストに注意してください。
  - レスポンスのバリデーションやリトライロジックを備えていますが、運用時はログと実際の書き込み結果を確認してください。

- 停止フラグのクリア
  - KILL_FLAG_CLEAR_ON_START が設定されていると起動時に kill.flag を自動で消します（本番では推奨されません）

開発・拡張のヒント
------------------
- モジュールは相互依存を小さくする設計になっており、ユニットテストで個別の関数（純粋関数）を簡単にテスト可能です（portfolio, research の関数など）。
- DuckDB 接続を受ける関数群は本番データにアクセスせず解析・研究用途で利用できます。
- AI 呼び出し部分は _call_openai_api を patch / mock することでテスト可能です。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ で確認できます（例: 0.1.0）
- ライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（リポジトリに含めてください）

問題・質問
----------
不明点や実行時の問題が発生した場合は、ログ（logs/）や .env 設定、SQLite/DuckDB のパス・権限をまず確認してください。必要であれば validate_config で設定を検証してください。

以上。