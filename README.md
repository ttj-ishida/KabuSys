README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を支援する Python コードベースです。  
主に以下の役割を持つコンポーネント群を含みます。

- ExecutionEngine: 発注ロジック / 発注管理 / リスク管理（実運用／ペーパートレード対応）
- Monitoring: システム稼働監視・注文監視・リスク監視・Kill Switch
- Research: DuckDB 上で動くファクタ計算・特徴量解析ユーティリティ
- Portfolio: 候補選定・配分・ポジションサイズ計算・リスク調整
- AI 製品群: ニュース NLP によるセンチメント判定、レジーム判定（OpenAI 使用）
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定など

主な設計方針:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV=paper_trading の場合のみ別DBを使用）
- DuckDB を分析用途、SQLite を監視／注文ログ用途に利用
- OpenAI（gpt-4o-mini）を使った NLP 処理は API キーが必須。失敗時はフェイルセーフで継続

機能一覧
--------
主な機能（抜粋）:

- 実行関連
  - ExecutionEngine 起動スクリプト (run_execution.py)
  - 発注管理（OrderManager / OrderRepository）
  - RiskManager（最大ポジション比率・利用率等の制限）
  - Reconciler によるブローカ差分調整
  - Paper Trading モード（MockBroker + data/paper_trading.db）

- 監視関連
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス存在確認）
  - TradeMonitor（滞留注文・約定異常検出 等）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（閾値到達時に data/kill.flag を作成）
  - MonitoringEngine（上記をまとめてポーリング）
  - 監視 DB の初期化とマイグレーション（monitoring_db.py）

- 研究・分析
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（Information Coefficient）計算
  - Paper Trading 検証レポート生成ツール

- AI（オプション）
  - ニュース集約 → OpenAI に投げて銘柄別センチメントを ai_scores に書込む（news_nlp.score_news）
  - マクロニュース + 1321 の MA200 を合成して市場レジーム判定（regime_detector.score_regime）

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - 統一ログ設定（utils.logging_setup）
  - プロセス優先度設定（utils.process_priority）

前提条件
--------
- Python 3.9+（型ヒント等を使用。プロジェクトの pyproject.toml を参照してください）
- 必要ライブラリの例（プロジェクトの requirements.txt を使ってインストールしてください）:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML の中身チェックを行う場合に必要）
- OpenAI を利用する機能は OPENAI_API_KEY が必要

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストールします。
   - pip install -r requirements.txt
   もしくは最低限:
   - pip install duckdb psutil openai pyyaml

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - あるいは手動で .env を用意（.env.example を参照してください）

4. 設定検証を実行して問題がないことを確認します。
   - python -m kabusys.validate_config
   - 本番準備で警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化は起動スクリプトが自動で行います（monitoring_db.init_monitoring_db が実行されます）。

主な環境変数（重要）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH を使用します
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API を使う機能で必要

使い方（起動・コマンド）
-----------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（例: MONITOR_POLL_INTERVAL=30）
    - 監視は settings.sqlite_path（SQLITE_PATH）に対して常に「本番」パスを使います（環境に依存しません）
    - 停止: data/stop_requested.flag を作成することでループを抜けます

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
    - 起動時に data/stop_requested.flag が存在する場合は起動せずに終了します
    - 実行中は PID ファイル（data/execution.pid）を作成します
    - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl-C）を送ってください

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（duckdb.connect(path)）
    - api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI API キーが必要

ロギング
--------
- setup_logging を起動スクリプトで呼び出して統一的にログを設定しています
- デフォルトで stdout と日次ローテーション（logs/<app_name>.log）に出力
- ログディレクトリは LOG_DIR またはデフォルト logs/

停止・Kill Switch
-----------------
- 停止フラグ:
  - 実行ループ停止用: data/stop_requested.flag（run_monitoring / run_execution が参照）
  - 実運用停止 (Kill Switch): data/kill.flag（KillSwitch が作成）
    - KillSwitch は RiskMonitor 等のアラートをトリガーに write します
    - clear 操作: KillSwitch.clear() を呼ぶかファイルを手動削除してください
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動でクリアします（本番では 0 推奨）

ディレクトリ構成（主要部分）
---------------------------
プロジェクトルートの src/kabusys を想定した主要ファイル／ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動ロード・Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意・ヒント
-------------------
- 環境ごとに DB を分離してください（特に本番とペーパートレード）。PAPER_TRADING_SQLITE_PATH を設定することで分離できます。
- OpenAI を利用する機能は API コスト・レートリミットに注意。リトライ・クリップロジックが備わっていますが、運用時はバッチ回数やサイズを調整してください。
- logs ディレクトリ作成に失敗した場合はファイルログが有効になりません。起動ユーザーの権限を確認してください。
- run_monitoring は MONITOR_POLL_INTERVAL で制御可能。短くしすぎるとリソースを消費します。
- 本番での自動 kill.flag クリアは危険（KILL_FLAG_CLEAR_ON_START は 0 推奨）。

開発・テスト
------------
- モジュールは単体関数が多く純粋関数設計の箇所があり、ユニットテストしやすくなっています（例: portfolio.*, research.*）。
- OpenAI 呼び出し部分は _call_openai_api をモックすることで外部 API を叩かずにテスト可能です。
- validate_config と config_setup は CI 前チェックとして有用です。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を追記してください）

以上。README の内容をベースに運用手順やドキュメントを整備してください。質問や追加で載せたい情報があれば教えてください。