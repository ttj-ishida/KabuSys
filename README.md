README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたPythonパッケージ群です。  
主な機能はトレード実行（本番・ペーパートレード）、監視・アラート、ポートフォリオ構築、ファクター計算／研究、ニュースのLLMによるセンチメントスコアリングなどを含みます。  
設計方針としては「安全性（本番/ペーパートレード分離）」「フェイルセーフ」「ルックアヘッドバイアスの回避」「単体関数化（副作用抑制）」を重視しています。

主な特徴
--------
- ExecutionEngine
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory により実アカウント／モックを選択
  - リスク管理（RiskManager）やオーダー管理（OrderManager）を組み込んだ発注エンジン
  - 起動時に実行ファイル（PID）や停止フラグの検査を実行

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite ベースの監視ログ（monitoring.db）と DuckDB（分析用）
  - Kill Switch（条件に応じて data/kill.flag を作成し Execution を停止）
  - ポーリングの間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL）

- ポートフォリオ構築（portfolio）
  - シグナルの候補選定、等金額 / スコア重み配分
  - セクター上限、レジーム乗数の適用
  - リスクベース／等配分の株数決定、単元株調整

- リサーチ（research）
  - DuckDB を用いたファクター計算（Momentum, Value, Volatility 等）
  - 将来リターン・IC 計算、統計サマリ

- AI / ニュース
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（ai.news_nlp）
  - マクロニュースと ETF の MA を組み合わせた市場レジーム判定（ai.regime_detector）
  - API 呼び出しはリトライ／バックオフ、レスポンスバリデーション済み

- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 起動前設定検証ツール（validate_config.py）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）

セットアップ
----------
前提
- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必要なライブラリ例:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の構文チェック用）

インストール例（仮想環境推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（プロジェクトに requirements.txt があればそちらを使用）
   - pip install duckdb psutil openai
   - （config YAML の検証を行う場合）pip install pyyaml

環境変数の準備
- 必須（少なくとも validate_config でエラーにならないように）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う設定（デフォルトがあるもの）
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL / LOG_DIR
  - OPENAI_API_KEY（AI 機能を使う場合）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定動作：instant/partial/never/reject）

.env 作成の手順（推奨）
1. 対話式ウィザードで作成
   - python -m kabusys.config_setup
   - 画面の指示に従い .env を生成

2. 生成後に設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます

使い方（起動方法）
-----------------
- ExecutionEngine を起動（当日のセッションを開始）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db に記録されます。本番 DB と分離されます。

- Monitoring を起動（常駐監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番の monitoring DB）を使用します。

- 停止 / Kill
  - 監視や実行はプロジェクトルート下の data/stop_requested.flag を監視しており、ファイルが存在すると安全に停止します。
  - KillSwitch (監視→実行停止) は data/kill.flag を作成します。Execution 起動時の KILL_FLAG_CLEAR_ON_START 設定に注意してください（本番では 0 推奨）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- .env の対話的生成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL にする）:
    - python -m kabusys.validate_config --strict

注意事項
---------
- モニタリング DB（monitoring.db）は run_monitoring が使用するため、MONITOR_POLL_INTERVAL 等の値を適切に設定してください。
- run_monitoring は監視のために本番 sqlite_path を使用します（実験環境でも同じ DB を使うため注意）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 SQLite を使用して発注ログを分離します。
- OpenAI を使用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API呼び出しはリトライを含みますが、API 欠如時には例外やフォールバック（macro_sentiment=0など）があります。
- logging は utils.setup_logging によってコンソールおよび logs/<app>.log に日次ローテーションで出力されます。必要に応じて LOG_DIR を設定してください。
- validate_config で警告・エラーが出る場合、起動前に解消することを推奨します（特に KABUSYS_ENV=live では注意が必要）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス：環境変数の集中管理、自動 .env ロード機能
- config_setup.py
  - .env を対話的に生成 / 更新するウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py        — ニュースセンチメントの LLM スコアリング
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py   — SQLite の監視テーブル/永続化層
  - system_monitor.py  — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py   — （注文ログ監視: スタレード注文、異常約定等）※実装参照
  - risk_monitor.py    — ドローダウン・ポジション上限監視
  - kill_switch.py     — Kill Switch（flag ファイル生成）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py   — （LINE 等への通知管理: 実装参照）
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
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- utils/
  - logging_setup.py
  - process_priority.py
  - （その他ユーティリティ）

付録：よく使う環境変数（抜粋）
--------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY (AI 機能に必要)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存ディレクトリ)
- PID_FILE_PATH (execution の PID ファイル)
- KILL_FLAG_PATH (kill.flag のパス)
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時に kill.flag を消すか

サポート / 貢献
----------------
- バグや改善提案は issue を立ててください。
- テストや機能追加はモジュール単位の分離を保ちながら行ってください（副作用を避けるため I/O を注入可能にしている箇所が多くあります）。

以上が概要と基本的な使い方の説明です。必要なら各モジュールの詳細なドキュメント（API、関数引数、戻り値、サンプル）も別途作成します。どの章を拡張したいか教えてください。