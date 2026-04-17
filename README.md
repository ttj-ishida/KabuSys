README — KabuSys (日本語)
========================

概要
----
KabuSys は日本株向けの自動売買／研究用フレームワークです。本リポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、ファクター計算、LLM を使ったニュースセンチメント解析などを含みます。設計の要点は以下の通りです。

- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した環境切替
- SQLite（監視・発注ログ等）と DuckDB（時系列データ / 研究用）を併用
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定の統合（任意）
- フラグファイル（kill.flag / stop_requested.flag）による安全シャットダウン機構
- 環境変数を .env / .env.local から自動読み込み（任意で無効化可）

主な機能
--------
- ExecutionEngine（run_execution）:
  - 実際の発注処理（本番）または MockBroker によるペーパートレード
  - Risk Manager、Order Manager、Reconciler 等と連携
  - 起動時に PID ファイルを出力し、stop フラグで安全停止
- Monitoring（run_monitoring / monitoring_engine）:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と dashboard の更新
  - KillSwitch: 危険条件で ExecutionEngine 停止フラグ（kill.flag）を書き込む
  - AlertManager（通知連携; 実装箇所に応じて LINE 等へ通知）
- Portfolio（選定・重み計算・ポジションサイズ算出）:
  - 候補選定、等金額／スコア加重、リスクベース割当て、セクターキャップ、レジーム乗数
- Research（ファクター計算・特徴量探索）:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの統計ツール
- AI（news_nlp / regime_detector）:
  - OpenAI を用いたニュースセンチメントスコアリング
  - マクロニュース + ETF MA200 による市場レジーム判定
- ツール:
  - config_setup: .env を対話式で作成・更新
  - validate_config: 起動前に環境変数 / 設定ファイルを検証
  - paper_verification_report: ペーパートレードの検証レポート出力

前提 / 依存
------------
- Python 3.10 以上（| 型等の構文を使用）
- 必須ライブラリ（代表）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config/ の YAML 検証を行いたい場合）
  - SQLite3（標準ライブラリ）
- インストール例:
  - pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートに移動
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
4. 対話式ウィザードで .env を作成（推奨）
   - python -m kabusys.config_setup
   - 生成された .env は Git 管理外にしてください（README 内にも注意あり）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict
6. 必要に応じてデータディレクトリを作成
   - デフォルトの DB 等は data/ 以下を想定しています（例: data/monitoring.db, data/kabusys.duckdb）

重要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を使う機能の API キー（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE — ペーパートレード時の約定モード: instant | partial | never | reject（default: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, default: 60）
- KILL_FLAG_CLEAR_ON_START — 本番での危険設定防止用（default: "0"。1 にすると起動時に kill.flag を自動クリア）

注意: 環境変数は .env / .env.local によって自動でロードされます（プロジェクトルートが検出される場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 動作: PID を data/execution.pid に出力、停止は data/stop_requested.flag を作成することでループを検知して停止
  - paper_trading の場合: MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを分離保存

- Monitoring を起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=<秒> でポーリング間隔を上書き（1 以上の整数）
  - 停止フラグ: data/stop_requested.flag を作成して監視を終了可能

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

フラグ / PID ファイル
--------------------
- data/execution.pid — ExecutionEngine が起動時に書き出す PID ファイル
- data/stop_requested.flag — run_execution / run_monitoring の外部停止用フラグ（ファイルが存在するとループを終了）
- data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine に重大な停止指示を与える（存在時はエンジンは停止される方向）

動作上の注意
------------
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を監視 DB として使用します（監視ログは単一の monitoring.db を想定）。
- モジュール内の LLM 呼び出し（news_nlp / regime_detector）は OpenAI API キーが必須。API 呼び出しに失敗した場合は安全側にフォールバックして処理を継続します（例: スコア = 0.0）。
- validate_config は config/*.yaml の存在と（PyYAML があれば）パースを検証します。これらの設定ファイルは scripts/generate_config.py 等で生成できます（プロジェクトに応じた運用をしてください）。
- MONITOR_POLL_INTERVAL は整数で 1 以上である必要があります。不正値の場合はデフォルト 60 秒が使用されます。

ディレクトリ構成 (src/kabusys)
------------------------------
以下は主要なファイル／パッケージの概観（完全な一覧ではありません）。

- __init__.py
- config.py — 環境変数 / .env の読み込みと Settings クラス
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores へ書き込む
  - regime_detector.py — マクロ + ETF MA に基づく市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル定義・永続化 API
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
- execution/
  - (OrderManager, ExecutionEngine, BrokerFactory 等、発注周りの実装)
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py（DuckDB を使ったファクター計算）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/、portfolio/、research/ 等の詳細な実装はコード内ドキュメントを参照してください。

開発上のヒント
----------------
- ログレベルは LOG_LEVEL 環境変数で調整できます（例: LOG_LEVEL=DEBUG）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを抑止できます。
- OpenAI 呼び出しはネットワーク/429/5xx に対してリトライ実装がありますが、API 利用料に注意してください。
- データ整合性のため、monitoring_db.init_monitoring_db() は冪等にテーブルと必要なカラムを作成します。既存 DB の軽微なマイグレーション処理も含まれます。

ライセンス / 貢献
-----------------
（ここにライセンスと貢献ガイドラインを追記してください）

おわりに
--------
この README はプロジェクトの主要機能と運用方法の概観を示しています。各モジュールには詳細な docstring と挙動が記載されていますので、実装や挙動の詳細は該当ソースファイルを参照してください。問題や要望があれば Issue を立ててください。