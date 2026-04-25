README
======

概要
----
KabuSys は日本株の自動売買システム（バックテスト・ペーパートレード・本番運用を想定）向けの Python コードベースです。本プロジェクトは次の機能群を提供します:

- データ取り込み / DuckDB を用いたファクタ計算（research）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- 発注実行レイヤ（ExecutionEngine、Paper Trading 用の分離 DB）
- 監視・アラート（System/Trade/Risk の定期チェック、Kill Switch）
- AI を用いたニュースセンチメント評価（OpenAI を利用）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証ツール 等）
- 運用向けツール（Paper Trading の検証レポート等）

主要な設計方針は「フェイルセーフ」「ルックアヘッドバイアス防止」「テスト容易性の確保」です。ペーパートレードは本番 DB と明確に分離され、AI 呼び出しは例外をサービス停止につなげないよう配慮されています。

主な機能
--------
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict オプションあり)
- 実行エンジン
  - run_execution: ExecutionEngine 起動スクリプト（本番 / paper_trading の切替）
  - paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
- 監視
  - run_monitoring: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔調整）
  - MonitoringEngine による System / Trade / Risk の集約監視、Kill Switch 書き込み・通知
- ポートフォリオ構築
  - 候補選定（score/ランク）/ 等配分・スコア加重 / リスク調整（セクターキャップ等）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）
- リサーチ
  - DuckDB を使ったファクター計算（momentum, value, volatility 等）
  - 特徴量探索、将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースのセンチメント評価（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
  - API 呼び出しはリトライ・バックオフ・パース検証等を実装
- 運用ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python 環境準備
   - 推奨: Python 3.10+（本リポジトリで明示はありませんが、型アノテーション等を想定）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config/*.yaml のパース検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

3. .env ファイル作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - 生成後、python -m kabusys.validate_config で検証してください。
   - 自動読み込み:
     - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。
     - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリ作成
   - SQLite / DuckDB / logs 等のパスは .env で指定できます。デフォルト:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - logs/
   - ログディレクトリはログ設定ユーティリティが自動作成しますが、権限等により失敗する場合があります。

5. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、該当 API 呼び出し関数に api_key を渡してください。

使い方（主なコマンド）
--------------------
- 設定関連
  - 対話式作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config
    - --strict をつけると警告もエラー扱いで終了コード 1 を返します

- 実行エンジン（Execution）
  - 起動: python -m kabusys.run_execution
  - 停止:
    - 実行中のエンジンは data/stop_requested.flag の作成で停止ループを検知して終了します（run_execution は終了時に pid ファイルを消す実装を想定）。
    - Kill Switch（条件発動）により data/kill.flag が書かれると外部で起動された ExecutionEngine に停止シグナルを送る運用ができます。

- 監視
  - 起動: python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を使用（Monitoring のログは本番 DB に書き込む設計）
  - 停止: data/stop_requested.flag を作成すると監視ループは終了します

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ API（プログラムから呼び出す）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - リサーチ関数: kabusys.research.calc_momentum/…（DuckDB 接続と日付を渡して使用）

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔, default: 60)
- OPENAI_API_KEY (AI 機能用)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか、0/1)

運用上の注意
------------
- paper_trading 環境は本番 DB と分離されるよう設計されています（settings.is_paper 判定）。
- OpenAI 等外部 API を使う処理は失敗時にフォールバックするよう実装されていますが、API キーの設定漏れ等に注意してください。
- 本番環境（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で変更可能です。
- プロセス優先度設定機能（utils.process_priority）はプラットフォーム権限に依存します。権限不足のときは警告を出してスキップします。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み・検証、自動 .env ロード機能を含む
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替、stop フラグ管理）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- utils/
  - logging_setup.py: ルートロガーの一括設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py: SQLite ベースの永続化層（テーブル作成・読み書きラッパー）
  - system_monitor.py: CPU/メモリ/Disk/データ鮮度/プロセス監視
  - trade_monitor.py: （該当ファイルの内容により詳細実装）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: data/kill.flag 書き込みロジック
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - alert_manager.py: （アラート送信の実装）
- execution/
  - execution_engine.py, order_manager.py, broker_factory.py, order_repository.py, reconciler.py, risk_manager.py
  - （発注実行 / リスク管理 / 注文記録）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py: ニュースセンチメント評価（OpenAI を使用）
  - regime_detector.py: レジーム判定（MA + マクロセンチメント）
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成ツール
- data/ (実行時に使用するファイル)
  - monitoring.db (SQLite), paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など
- logs/ (ログファイル出力先; ログ設定により自動作成)

開発・拡張のヒント
------------------
- DuckDB 接続を渡して研究用関数（research.*）を呼ぶことで、分析処理を本番データに対して安全に実行できます。
- AI 呼び出しは _call_openai_api を patch することでユニットテスト中に差し替え可能です（テスト容易性を考慮した設計）。
- 設定の自動ロードはプロジェクトルート検出に .git または pyproject.toml を使用します。パッケージ化・配布後も期待どおりに動作します。
- monitoring_db.init_monitoring_db は冪等でスキーマのマイグレーション（カラム追加）も含みます。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（本 README にライセンス文は含めていません）。

問い合わせ
----------
不明点や拡張提案があれば、リポジトリの Issue を立てるか、担当チームに直接お問い合わせください。

以上。