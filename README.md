README
=====

概要
----
KabuSys は日本株自動売買システムのライブラリ群です。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 発注実行エンジン（ExecutionEngine）の起動スクリプト run_execution
- システム監視（Monitoring）の起動スクリプト run_monitoring と各種モニタ
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- AI（LLM）を用いたニュースセンチメント評価・レジーム判定
- .env の対話式セットアップ・設定検証ツール
- Paper Trading の検証レポート作成ツール

設計方針の要点:
- 設定は .env（環境変数）を基本とする。プロジェクトルートの .env/.env.local を自動読み込み。
- DuckDB と SQLite をデータ層に使用（デフォルト: data/kabusys.duckdb, data/monitoring.db）。
- 本番/ペーパートレードを環境変数 KABUSYS_ENV で切替（development / paper_trading / live）。
- LLM 呼び出しは OpenAI SDK を利用。APIキーは OPENAI_API_KEY で設定。
- 可能な限りフェイルセーフ（API失敗時のフォールバック等）を採用。

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録）
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能）
- 設定管理
  - kabusys.config: .env 自動読み込み・Settings 型による設定取得
  - python -m kabusys.config_setup: 対話式ウィザードで .env を作成/更新
  - python -m kabusys.validate_config: .env や config/*.yaml の起動前検証（--strict あり）
- モニタリング
  - system_monitor: CPU/メモリ/Disk、プロセス生存、データ鮮度を監視
  - trade_monitor / risk_monitor / monitoring_engine / kill_switch: 注文滞留やドローダウンを監視し必要時に kill.flag を書き込む
  - monitoring_db: SQLite にログ・ダッシュボード等の永続化
- ポートフォリオ
  - ポジション候補選定、等重/スコア重み、セクター上限・レジーム乗数、株数計算（単元丸め・集計上限処理）
- 研究（research）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- AI（LLM）
  - news_nlp.score_news: raw_news を集約して OpenAI API で銘柄ごとのセンチメントを取得・ai_scores に書き込む
  - regime_detector.score_regime: ETF MA と LLM マクロセンチメントを合成して market_regime に保存
- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

前提 / 推奨環境
----------------
- Python 3.10+（コードは union 型記法など Python 3.10 以降の構文を使用）
- 推奨パッケージ（一例）:
  - duckdb
  - openai
  - psutil
  - PyYAML（config.yaml 検証を行う場合）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI API を利用する機能を使う場合）

インストール（例）
-----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai psutil PyYAML

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

設定（.env）
-----------
- 推奨フロー:
  1. python -m kabusys.config_setup を実行して、対話式ウィザードで .env を作成/更新
  2. python -m kabusys.validate_config で設定検証（--strict を付けると警告もエラー扱い）

- 主要な環境変数:
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 動作モード:
    - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - データパス:
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
  - ログ:
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - LOG_DIR（ログ保存先、デフォルト logs/）
  - OpenAI:
    - OPENAI_API_KEY（AI 機能利用時に必要）
  - Monitoring / Execution:
    - PID_FILE_PATH（実行プロセス用 pid ファイルパス、デフォルト data/execution.pid）
    - KILL_FLAG_PATH（kill.flag のパス、デフォルト data/kill.flag）
    - KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に kill.flag を自動クリア（本番では 0 推奨）
  - Paper Trading:
    - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト instant）
  - Monitoring のポーリング間隔:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60。0以下は無効でデフォルトにフォールバック）

使い方（主要コマンド）
---------------------
- .env の作成（対話式ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番/開発（環境に応じて KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 動作中の停止: プロジェクトルート/data/stop_requested.flag を作成するとスレッドが終了する。エンジン停止は kill.flag によるシグナルで実行される設計。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能（OpenAI API 必須）
  - news_nlp.score_news / regime_detector.score_regime はコードから呼び出して利用します（OPENAI_API_KEY を設定）
  - 例: python スクリプト内で kabusys.ai.news_nlp.score_news(duckdb_conn, date(2026,4,1))

運用上の注意
--------------
- Monitoring 実行時は monitoring 側は Settings.sqlite_path（デフォルト: data/monitoring.db）を環境に関係なく使用します（監視ログは本番 DB を参照）。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_db を使用して本番 DB と分離します。
- Kill Switch（KillSwitch）は RiskMonitor 等の結果を評価して data/kill.flag を書き込みます。ExecutionEngine はこのフラグを監視して自己停止します。KILL_FLAG_CLEAR_ON_START に注意してください（本番は 0 推奨）。
- ログは logs/<app_name>.log（デフォルト）に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 配下の主要ファイル・モジュール）
- __init__.py
- config.py                : 環境変数/.env の自動読み込みと Settings
- config_setup.py          : .env 対話式ウィザード
- validate_config.py       : 設定検証 CLI
- run_execution.py         : ExecutionEngine 起動スクリプト
- run_monitoring.py        : SystemMonitor ポーリングスクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py            : ニュースの LLM スコアリング
  - regime_detector.py     : 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       : SQLite 永続化層
  - monitoring_engine.py   : 複数モニタを束ねるエンジン
  - system_monitor.py      : CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py        : ドローダウン・ポジション上限監視
  - kill_switch.py         : kill.flag 管理
  - (trade_monitor, alert_manager 等が存在)
- execution/                : 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等）
- portfolio/
  - portfolio_builder.py   : 候補選定・重み計算
  - position_sizing.py     : 株数決定・集約上限処理
  - risk_adjustment.py     : セクター上限・レジーム乗数
- research/
  - factor_research.py     : momentum/value/volatility 等
  - feature_exploration.py : 将来リターン、IC、統計サマリ
- data/                     : データファイル（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
- tools/
  - paper_verification_report.py

補足（実装上のポイント）
-----------------------
- process_priority.set_process_priority により起動時にプロセス優先度を上げる（可能な場合）。
- logging_setup.setup_logging により stdout と日次ローテートファイルへ統一的にログ出力。
- DuckDB 接続は研究・AI・分析処理で活用。SQLite は監視/取引ログの永続化に使用。
- LLM 呼び出しはリトライとレスポンスバリデーションを行い、部分失敗時に既存データを保護するために書き込みを絞る設計。

よくある操作例
--------------
- 開発環境でペーパートレード実行:
  1. KABUSYS_ENV=paper_trading を .env に設定（または環境変数で設定）
  2. python -m kabusys.run_execution
  3. 実行後、 data/paper_trading.db を分析・検証

- 監視サービスの起動（例: systemd / supervisor で常駐）:
  - 実行コマンド: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境で設定してポーリング間隔を調整可能

問い合わせ / 開発メモ
-------------------
- 設定ファイルのテンプレートは .env.example（存在する場合）を参照してください。
- config/*.yaml（system_config.yaml 等）は config_setup で生成/編集できます（generate_config スクリプトがある場合）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを抑止できます。

以上。必要に応じて README をプロジェクト固有の手順（CI 設定、systemd ユニット例、requirements.txt の正確な内容など）で拡張してください。