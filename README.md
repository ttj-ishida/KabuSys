README (日本語)
===============

概要
----
KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。本リポジトリは以下の主要コンポーネントを含みます：
- 発注実行エンジン（ExecutionEngine）: 実口座 / ペーパートレード両対応の注文処理。
- 監視サブシステム（Monitoring）: システム稼働状況、注文・リスク監視、Kill Switch。
- 研究・ファクター計算（Research）: DuckDB 上でファクター計算・特徴量解析。
- ニュース NLP / レジーム検出（AI）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定。
- ポートフォリオ構築ユーティリティ（Portfolio）: 候補選定、重み算出、ポジションサイズ計算等。
- 運用ツール（tools）: ペーパートレード検証レポート生成など。
- 設定/ユーティリティ（config, utils）: .env ウィザード、設定検証、ログ設定、プロセス優先度制御 等。

主な設計方針
- 本番/ペーパートレードを環境変数 KABUSYS_ENV で切替。
- DuckDB を分析用 DB、SQLite を監視・注文ログ用に利用。
- OpenAI API を使う処理は明示的に APIキーを要求しフォールバックやリトライを行う（フェイルセーフ）。
- モジュールは副作用を最小にし、純粋関数的な実装を心掛ける箇所あり（research / portfolio 等）。

機能一覧
---------
- 実行:
  - ExecutionEngine による注文発行・約定管理（本番／ペーパートレード切替）。
  - BrokerClientFactory によるブローカークライアント抽象化（ペーパートレードでは Mock を使用）。
- 監視:
  - SystemMonitor：CPU/メモリ/ディスク監視、データ鮮度チェック、Execution プロセス監視。
  - TradeMonitor：注文滞留／約定異常等の検出（実装箇所が本README のコードに含まれている想定）。
  - RiskMonitor：ドローダウン／ポジション上限監視とログ記録。
  - KillSwitch：条件に応じた data/kill.flag の書き込みで実行エンジン停止をトリガー。
  - MonitoringEngine：上記の統合ポーリングループ。
- 研究・解析:
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、特徴量統計。
- AI:
  - news_nlp.score_news：ニュース記事を集約して OpenAI に投げ、銘柄別スコアを ai_scores に書き込み。
  - regime_detector.score_regime：ETF の MA とマクロニュースの合成で市場レジーム判定。
- 運用ツール:
  - config_setup：.env の対話式生成・更新ウィザード。
  - validate_config：環境変数・config/*.yaml の起動前検証。
  - tools.paper_verification_report：ペーパートレード履歴から検証レポート生成。

前提条件
--------
- Python 3.10+
- 依存ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- OS: Windows / Linux / macOS を想定（プロセス優先度などはプラットフォームに依存して動作する箇所あり）

セットアップ手順
----------------
1. リポジトリを取得:
   - git clone <repo-url>
2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール:
   - pip install -r requirements.txt
   （requirements.txt がない場合は上述の主要依存パッケージを個別にインストールしてください）
4. 初期設定（.env）:
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記「主な環境変数」を参照）
5. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば .env を修正し、再度検証してください。
6. データディレクトリの準備:
   - デフォルトでは data/ 配下に DB・フラグファイルを作成します。適切なパスを .env で指定してください。
7. DuckDB / SQLite の初期化:
   - 実行スクリプトが起動時に必要テーブルを作成します（init_monitoring_db を通じて冪等に作成）。

主な環境変数（抜粋）
------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / オプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: Mock ブローカー & data/paper_trading.db を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で True）
- PID_FILE_PATH, KILL_FLAG_PATH — 各種フラグ / PID のパスは Settings で上書き可能

使い方（コマンド）
-----------------
- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります
- 実行エンジン起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録されます
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します
- 監視ループ起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - data/stop_requested.flag を検知すると監視ループを終了
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - 指定がなければ PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照

ログ / 運用
-----------
- ログ出力は kabusys.utils.logging_setup.setup_logging を用いて統一的に行われ、stdout と 日次ローテーションファイル（logs/<app_name>.log）に出力します。
- 各起動スクリプトは起動時に set_process_priority("high") を呼び出してプロセス優先度を上げようとします（権限や OS によりスキップされる場合があります）。
- 停止制御:
  - 管理者が ExecutionEngine を止めたい場合は data/kill.flag を作成するか、監視が KillSwitch 条件を満たした際に自動で作成します。
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループを優雅に終了できます。

開発者向け API（概要）
--------------------
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.ai: score_news（ニュース NLP）, regime_detector.score_regime
- kabusys.monitoring: MonitoringDB, SystemMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager（想定）
- utils: logging_setup.setup_logging, process_priority.set_process_priority / set_cpu_affinity

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings クラス（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

subpackages:
- execution/   — 発注エンジン関連（BrokerFactory, EngineConfig, ExecutionEngine, OrderManager, Reconciler, RiskManager, OrderRepository 等）
- monitoring/  — 監視関連（monitoring_db.py, system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等）
- portfolio/   — ポートフォリオ構築用純粋関数（portfolio_builder.py, position_sizing.py, risk_adjustment.py）
- research/    — ファクター計算・特徴量ツール（factor_research.py, feature_exploration.py）
- ai/          — news_nlp.py, regime_detector.py（OpenAI API を使用）
- utils/       — logging_setup.py, process_priority.py 等
- tools/       — 運用ツール（paper_verification_report.py 等）
- monitoring/monitoring_db.py — SQLite テーブル作成・永続化 API

（注）上記は主要ファイルの抜粋です。詳細はソースコードコメントを参照してください。

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番運用につながります。J-Quants / kabu API 等の資格情報や通知設定（LINE）を確実に設定してください。
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- OpenAI API の利用はコストがかかります。news_nlp / regime_detector の毎回の呼び出し頻度とバッチ化設定に注意してください。
- データ鮮度や DB のバックアップ、ログローテーションの確認を定期運用フローに含めてください。

貢献・開発
-----------
- 新機能追加や不具合修正は PR をお願いします。コード内のドキュメントとコメントを尊重して実装してください。
- テストはユニットテストで pure 関数（portfolio / research 等）を重点的にカバーすることを推奨します。外部 API 呼び出し部はモック化してください（例: news_nlp._call_openai_api の patch）。

参考: 最小 .env 例
-----------------
（実際は secret 値を設定してください）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_key

以上。開発・運用で不明点があれば、該当モジュールの docstring やソースコメントを参照してください。