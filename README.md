# KabuSys

日本株向け自動売買システムの骨格ライブラリ / 実行スクリプト群です。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、LLM を使ったニュース解析等の主要コンポーネントで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件
- セットアップ手順
- 環境変数（.env）
- 使い方（起動例）
- 主要ファイル／スクリプト説明
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコアロジック群です。
- 発注処理（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ（ファクター計算 / 特徴量解析）、AI（ニュースセンチメント・レジーム判定）などの機能を備えています。
- DB は分析用に DuckDB、監視／発注ログ用に SQLite を使用します。ペーパートレード（分離実行）モードでは paper_trading 用の専用 SQLite を使用して本番データと完全分離します。

主な機能一覧
- Execution
  - ExecutionEngine（発注処理の起動と管理）
  - BrokerClientFactory により本番ブローカ／モックブローカを切り替え可能（KABUSYS_ENV=paper_trading）
  - リスク管理（RiskManager）、注文管理（OrderManager / OrderRepository）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件により data/kill.flag を生成して Execution を停止）
  - Monitoring DB（SQLite）初期化 / 永続化ロジック
- Portfolio
  - 候補選定 / ウェイト計算（等金額・スコア加重）
  - セクター上限適用、レジーム乗数、株数決定（lot 丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp: OpenAI (gpt-4o-mini) を使ったニュースの銘柄別センチメントスコア化（ai_scores へ書込）
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定
- ツール
  - paper_verification_report: ペーパートレードの検証レポート生成（稼働率、注文成功率、レイテンシ等）

動作要件
- Python 3.10 以上（型注釈に | を使用しているため）
- 必須パッケージ（例）
  - duckdb
  - psutil
- AI 機能を使う場合:
  - openai（OpenAI Python SDK）
- 開発時の追加（オプション）
  - PyYAML（config ファイル検証用）
- SQLite は標準ライブラリで利用可

推奨の requirements.txt（例）
- duckdb>=0.6
- psutil>=5.9
- openai>=1.0   # AI 機能を使う場合
- PyYAML>=6.0   # config 検証を行う場合（任意）

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記パッケージを個別に pip install）

4. 初期 .env を作成
   - 対話式ウィザードを実行して .env を生成できます:
     - python -m kabusys.config_setup
   - ウィザードは .env を編集して保存します（.env は絶対に Git へコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

初期 DB / データディレクトリ
- デフォルトのパス（.env 未設定時）:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- これらの親ディレクトリがなければ、起動時に自動作成されることがあります（スクリプト側で mkdir 実行）。

主要な環境変数（代表）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 一般:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- AI:
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- Monitoring / Kill:
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（注意: 本番では 0 推奨）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- 監視ループ間隔:
  - MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒。デフォルト 60）

使い方（起動例）
- ExecutionEngine（発注エンジン）を起動
  - 本番（設定済み .env の KABUSYS_ENV が live の場合は本番ブローカを使用）
    - python -m kabusys.run_execution
  - ペーパートレード（本番データと分離、MockBroker を使用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に data/stop_requested.flag があると起動しません（停止フラグ）。
  - 実行中は data/execution.pid に PID が書き込まれます。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を参照して監視ログを書き込みます（環境にかかわらず）。

- Kill Switch（手動で Execution 停止）
  - KillSwitch は条件に応じて data/kill.flag を書き込むことで Execution 停止を指示します。
  - Clear したい場合は KILL_FLAG_CLEAR_ON_START を利用するか、手動でファイルを削除してください:
    - rm data/kill.flag

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

ログレベル設定
- .env の LOG_LEVEL で制御します（INFO デフォルト）。validate_config でも検証します。

停止フラグ / 仕組み
- data/stop_requested.flag: run_execution.py / run_monitoring.py はこのファイルを検出するとループを停止してプロセスを終了します（外部停止用）。
- data/kill.flag: KillSwitch が書き込む停止スイッチ。ExecutionEngine はこれを検出して停止します（設定により起動時に自動クリア可能）。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py: パッケージ初期化、バージョン情報
  - config.py: 環境変数・設定管理（.env の自動ロード・パース、Settings クラス）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により Mock/Broker 切替）
  - run_monitoring.py: SystemMonitor 単体のポーリング起動スクリプト
  - tools/
    - paper_verification_report.py: ペーパートレードの検証レポート生成
  - portfolio/
    - portfolio_builder.py: 候補選定・配分（等重・スコア加重）
    - position_sizing.py: 株数計算・単元丸め・集約キャップ処理
    - risk_adjustment.py: セクター上限、レジーム乗数
  - research/
    - factor_research.py: モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI で銘柄別スコアを取得して ai_scores に保存）
    - regime_detector.py: MA200 とマクロニュースの LLM センチメントを合成して market_regime 判定
  - monitoring/
    - monitoring_db.py: SQLite のスキーマ初期化 / 永続化 API
    - system_monitor.py: システム状態・データ鮮度チェック
    - trade_monitor.py: 注文滞留・約定異常チェック
    - risk_monitor.py: ドローダウン・ポジション数監視
    - kill_switch.py: Kill Switch 実装（flag ファイル操作）
    - monitoring_engine.py: 各 Monitor を束ねる実行ループ
    - alert_manager.py: （通知管理。コードベース冒頭に存在）
  - execution/, strategy/, data/ 等のサブパッケージ（発注ロジック、データパイプライン等）
  - utils/
    - process_priority.py: プラットフォームに依存しないプロセス優先度設定ユーティリティ
  - その他: order_repository, order_manager, reconciler, risk_manager 等（発注ロジック群）

設計上の注意点 / 実運用向けガイド
- .env は絶対にリポジトリにコミットしないこと。
- 本番環境で KABUSYS_ENV=live を使う際は LINE 通知等の設定を必ず確認してください（validate_config にて警告あり）。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です（推奨は 0）。
- AI 機能は OpenAI の API 利用料が発生します。API キーの管理・クォータに注意してください。
- run_execution/run_monitoring は stop_requested.flag（data/stop_requested.flag）を検出して安全に停止します。外部運用監視やコンテナ停止処理と併用してください。
- Monitoring は監視 DB を通じて冪等的にログ・状態を書き込みます。init_monitoring_db() によりスキーママイグレーションも一部自動適用されます。

トラブルシューティング
- PyYAML がインストールされていないと validate_config の YAML 検証はスキップされます（警告）。必要に応じて PyYAML をインストールしてください。
- DuckDB 接続周りはローカルファイルのパス権限を確認してください。
- psutil を使ったプロセス優先度設定は権限が必要な場合があります。AccessDenied の場合はログに警告が出てスキップされます。

---

その他
- ドキュメントや設計（PortfolioConstruction.md, StrategyModel.md 等）が参照されています。これらが同梱されている場合は設計書に従ってパラメータ調整を行ってください。
- 追加のユーティリティや実装詳細は各モジュールの docstring（コード内コメント）を参照してください。

必要であれば README に記載するサンプル .env テンプレート、requirements.txt、または起動・デバッグ手順（例: ローカルでのペーパートレード手順・ログ確認方法）を追記します。どの情報を追加希望か教えてください。