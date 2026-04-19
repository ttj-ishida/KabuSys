KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株の自動売買および関連する研究・監視ツール群を含むモジュール群です。  
README は日本語で、プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめています。

プロジェクト概要
--------------
KabuSys は以下を目的とした Python ベースのパッケージです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine による発注（本番 / ペーパートレード分離）
- 監視コンポーネント（System / Trade / Risk monitoring）と Kill Switch
- AI（OpenAI）を使ったニュースセンチメント / レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
--------
- モジュール設計（portfolio, research, ai, monitoring, execution, utils）
- DuckDB / SQLite を用いた分析・運用データ管理
- 本番（live） / ペーパートレード（paper_trading）を環境で分離
- Kill Switch（データ駆動で実行エンジン停止）実装
- OpenAI を利用したニュースセンチメント計算（API リトライ・バリデーション実装）
- ロギングは統一的に setup_logging で設定（stdout + 日次ローテートファイル）

機能一覧
--------
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて実ブローカー / Mock を自動選択）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理 / ツール
  - config_setup.py: .env を対話的に作成・更新するウィザード
  - validate_config.py: .env および config/*.yaml の起動前検証 CLI
- 監視
  - monitoring/monitoring_db.py: 監視用 SQLite スキーマ・永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager（アラート送信ロジック）
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・等分/スコア重み計算
  - portfolio.position_sizing: 単元丸め・リスクベース株数決定・aggregate cap
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン、IC（Spearman）計算、統計サマリ
- AI
  - ai.news_nlp: raw_news をまとめて OpenAI に投げ、ai_scores を更新
  - ai.regime_detector: ETF + マクロニュースで日次レジーム判定（market_regime へ冪等書込）
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

必要条件（想定）
----------------
- Python 3.10+
- 主要依存（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証オプションで必要）
- OS: Linux/macOS/Windows（psutil に依存する処理は権限やプラットフォームで動作差異あり）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （実プロジェクトでは requirements.txt があれば pip install -r requirements.txt）
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - デフォルトの DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 環境時）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付与

基本的な使い方
--------------
- Execution（エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を環境変数に設定すると MockBroker を使い、paper_trading 専用 DB に書き込みます。
  - 起動時に data/kill.flag が存在する場合は起動を抑止します（Kill Switch）。
  - プロセス PID は data/execution.pid に書き込まれます（pid_file のパスは Settings で変更可）。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視スクリプトは停止フラグ data/stop_requested.flag を検知するとループを終了します。
- Kill Switch
  - KillSwitch は条件が満たされた際に data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を参照して自動クリア挙動を制御します（本番は 0 推奨）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
    - conn は duckdb.connect(...) で得た接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
- ポートフォリオ関数の利用例（ライブラリとして）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_equal_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
- ロギング
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一的なログ出力を行います。
  - デフォルトログディレクトリ: logs/
  - ログレベルは LOG_LEVEL 環境変数または .env で設定

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時の kill.flag 自動クリア (0/1)

停止・フラグ関連
----------------
- ExecutionEngine 停止のため: data/kill.flag を作成します（KillSwitch が作成）。
- Monitoring 停止のため: data/stop_requested.flag を作成すると monitoring ループが終了します。
- PID ファイル: data/execution.pid（ExecutionEngine が書き込み）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動ロード・Settings
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルが存在する想定)
  - execution/                      — ExecutionEngine 関連（broker_factory 等: 実装に依存）
  - tools/
    - paper_verification_report.py
    - __init__.py
  - research/, portfolio/ などのモジュールは DuckDB 接続を受け取り純関数的に動作（テストしやすい設計）

開発時の注意点 / 運用のヒント
-----------------------------
- .env は決して Git にコミットしないこと（config_setup で注意書きあり）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE の通知設定を確認してください。
- OpenAI を使う機能は API 利用料と遅延を伴います。失敗時のフォールバックが各モジュールに実装されていますが、運用ルールを決めてください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）を事前に用意する必要があります。データパイプラインが別途必要です。
- psutil を使ったプロセス優先度設定は権限に依存します（root / 管理者権限が必要になる場合あり）。

よくあるコマンド例
------------------
- .env を作る
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。）

補足
----
この README はソースコードのヘッダや docstring を基に作成しています。各モジュールの詳細な挙動や外部依存（DB スキーマ、broker 実装、alert_manager 実装など）はソースコード内ドキュメントを参照してください。必要であれば各モジュールの使用例や API リファレンスを追加で作成できます。