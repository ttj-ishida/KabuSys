README
======

概要
----
KabuSys は日本株向けの自動売買／研究ソフトウェア群です。本リポジトリは以下の主要機能を含みます：

- 注文実行エンジン（ExecutionEngine） — 本番 / ペーパートレード両対応
- 監視・アラート（Monitoring） — システム状態、注文状況、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、IC 計算、特徴量探索）
- AI 連携（ニュース NLP によるセンチメント評価・レジーム判定、OpenAI 使用）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

この README はコードベースの主要な使い方と構成を説明します。

主な機能一覧
------------
- run_execution: 注文実行エンジンを起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading.db に記録（本番 DB と分離）。
- run_monitoring: SystemMonitor を周期的に実行して system_status やリスクを監視。MONITOR_POLL_INTERVAL で間隔変更可能。
- monitoring_engine: System / Trade / Risk モニタを統合して定期実行、Kill Switch の評価とアラート送出。
- monitoring_db: SQLite ベースの永続層（テーブル生成・マイグレーション含む）。
- portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制約、レジーム乗数。
- research: DuckDB を用いたファクター計算（Momentum / Volatility / Value）、将来リターン、IC、統計サマリ。
- ai: OpenAI を用いたニュースセンチメントスコアリング（news_nlp）と市場レジーム判定（regime_detector）。
- utils: ロギング設定、プロセス優先度 / CPU アフィニティ設定等のユーティリティ。
- tools.paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等を評価）。

前提（依存）
------------
最低限必要なライブラリ（実行する機能により追加で必要）:
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル YAML 内容検証を行う場合）

インストール例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

（プロジェクトには requirements.txt がないため、必要なものを用途に合わせてインストールしてください）

環境変数（主なもの）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db（監視ログ）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード: instant | partial | never | reject（デフォルト: instant）

運用上のファイル（デフォルトパス）
- data/execution.pid — ExecutionEngine の PID ファイル（設定経由で上書き可）
- data/kill.flag — Kill Switch が書き込む停止フラグ（Settings.kill_flag_path）
- data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ（プロジェクト内で使用）

セットアップ手順
----------------
1. リポジトリをクローン、仮想環境作成、依存パッケージをインストール。
2. .env の初期作成:
   - 対話式ウィザードを実行して .env を作成できます:
       python -m kabusys.config_setup
   - 生成後、必要な秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を入力してください。
3. 設定検証:
       python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
4. DB の準備:
   - run_execution / run_monitoring 実行時に sqlite/duckdb ファイルは自動で作成・初期化されます（monitoring 用テーブルは init_monitoring_db により作成）。
5. ログディレクトリ:
   - デフォルトは logs/。パーミッション確認を行ってください。

使い方（実行例）
----------------
- 環境ファイル作成:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視プロセス起動（デフォルトポーリング 60 秒）:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH に記録されます。
  - start 前に data/stop_requested.flag が存在すると起動を中止します。

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使います。

停止・Kill Switch
----------------
- 運用中に Kill Switch を作動させると ExecutionEngine に停止命令を送るため、監視コンポーネントが data/kill.flag を書きます。
- run_execution / run_monitoring は stop_requested.flag（data/stop_requested.flag）をチェックして外部停止を行います（外部で停止を要求する場合はこのファイルを作成してください）。

ロギング
--------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用し、
  stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定します。
- LOG_DIR 環境変数でログ保存先を変更可能。

注意点 / 運用メモ
-----------------
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能（news_nlp, regime_detector）は OpenAI API を使用し、API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライやフォールバック処理（失敗時は安全側の値を使用）を組み込んでいます。
- config モジュールはプロジェクトルートを .git または pyproject.toml で検出し、.env/.env.local の自動読み込みを行います。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority ユーティリティで優先度を "high" に設定します（権限不足の場合は警告ログを出してスキップ）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数・設定管理
- config_setup.py — .env 作成ウィザード（CLI）
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

パッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメントスコア
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義・永続化 API
  - system_monitor.py — システム状態 / データ鮮度チェック
  - trade_monitor.py — （省略）取引ログ監視ロジック
  - risk_monitor.py — ドローダウン・ポジション制限監視
  - kill_switch.py — Kill Switch 実装（flag ファイル）
  - monitoring_engine.py — モニタ群の統合実行
  - alert_manager.py — （省略）アラート送信ロジック（LINE 等）
- execution/ (注文関連コンポーネント群)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・資金配分ロジック
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py — ロギング初期化ヘルパ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py など（上記に含む）

ライセンス / 貢献
-----------------
（本 README にライセンス情報は含まれていません。リポジトリの LICENSE を参照してください）

最後に
------
運用開始前に必ず python -m kabusys.validate_config による検証を行い、.env の必須値（特に JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD、OpenAI を使う場合は OPENAI_API_KEY）を設定してください。問題がある場合はログ（logs/ 以下）を参照してトラブルシュートしてください。