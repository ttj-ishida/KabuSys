README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買 / 研究用ライブラリ群と、実運用向け実行エンジン・監視機能を含むプロジェクトです。本リポジトリには以下の主要機能が実装されています。

- ExecutionEngine（発注エンジン）: 実口座 / ペーパートレード両対応
- Monitoring（監視）: システム稼働状況・注文状況・リスク監視・Kill Switch
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research: ファクター計算（momentum/value/volatility）や特徴量解析ツール
- AI 支援: ニュースを LLM でスコアリングするモジュール、レジーム検出
- 各種ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード / 検証ツール、レポート生成 等

主な機能一覧
--------------
- 環境設定
  - .env の対話式生成（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
- 実行エンジン
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により paper_trading（モックブローカー）と live を切替
  - Paper trading は data/paper_trading.db（デフォルト）に分離保存
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを実行。監視ログは SQLite（data/monitoring.db）へ保存
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ね、Kill Switch と通知を扱う
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等重、スコア重み）
  - ポジションサイズ計算（リスクベース、等分配等）、単元株丸め、集約キャップ処理
  - セクター集中制限、レジーム乗数
- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- AI（OpenAI）
  - ニュースを LLM でスコア化し ai_scores に保存（kabusys.ai.news_nlp）
  - マクロニュース＋ETF の MA200 乖離から市場レジームを判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.10 以上を推奨（型注釈・最新ライブラリ互換のため）
- 仮想環境を利用することを推奨（venv / virtualenv / poetry 等）

1. 仮想環境の作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb psutil openai
   - 開発用・オプション:
     - pip install PyYAML
   （プロジェクトに requirements.txt がない場合、上記を目安にインストールしてください）

3. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは手動で .env をプロジェクトルートに作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に設定
   - 自動読み込み:
     - .env と .env.local は自動読み込みされる（OS 環境変数が優先）
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

使い方（主要コマンド）
---------------------

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）
    - python -m kabusys.validate_config --strict

- 監視ループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を変更可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するか Ctrl+C
  - 監視は常に本番用 sqlite_path を使います（KABUSYS_ENV に依らず）

- 実行エンジン起動（Execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録
  - python -m kabusys.run_execution
  - 停止: data/stop_requested.flag またはエンジン内部からの停止（Kill Switch 等）
  - 実行時は data/execution.pid に PID を書く（設定により変更可）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（コードから利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

主要設定 / 挙動のポイント
-----------------------
- 環境の分離
  - KABUSYS_ENV=paper_trading のとき、Execution は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使います。本番 DB と完全分離されます。
- Kill Switch / Stop フラグ
  - KillSwitch は Settings.kill_flag_path（デフォルト: data/kill.flag）を書き込むことで実行エンジンの停止をトリガーします。
  - 全体停止フラグ stop_requested.flag（data/stop_requested.flag）を配置すると run_monitoring / run_execution がループを抜けます。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。1 以上でない値は無視され、デフォルト 60 秒を使用。
- ログ設定
  - ログは stdout に出力され、また日次ローテーションで logs/<app_name>.log に保存されます（logs ディレクトリが作成できない場合はファイル出力はスキップされます）。
  - LOG_LEVEL / LOG_DIR で制御可能。
- OpenAI / LLM
  - AI 機能を使うには OPENAI_API_KEY を設定するか、API キーを関数引数に渡してください。
  - LLM 呼び出しはリトライ・バックオフ処理やレスポンス検証を備えていますが、API キー未設定時はエラーになります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                - 環境変数ロード・Settings
- config_setup.py          - .env 対話式ウィザード
- validate_config.py       - 起動前検証 CLI
- run_monitoring.py        - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         - ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py       - ロギング初期化
  - process_priority.py    - プロセス優先度設定（psutil ベース）
- monitoring/
  - monitoring_db.py       - SQLite 永続化層
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py       - （コードベースに存在、監視ロジック）
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py       - （通知処理）
- execution/
  - execution_engine.py    - ExecutionEngine 本体
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
- data/
  - pipeline.py            - DuckDB / データパイプライン参照関数（例: get_last_price_date）
  - stats.py               - 統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py

（上記は代表的なファイルのみ。詳しい実装は各モジュールの docstring を参照してください）

開発者向けメモ
---------------
- DB 初期化:
  - monitoring_db.init_monitoring_db(conn) は冪等にテーブルと必要なカラムを作成します。既存 DB に対してマイグレーション処理も含まれます。
- テストしやすさ:
  - news_nlp._call_openai_api などはテスト時にパッチしやすい設計になっています（unittest.mock.patch を想定）。
- セキュリティ:
  - .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意文あり）。
- 追加ツール:
  - validate_config は PyYAML がない場合に YAML の検証をスキップします。PyYAML を入れると config/*.yaml のパース検証が行われます。
- プラットフォーム差分:
  - process_priority は Windows / POSIX を吸収する実装です。権限不足等で失敗する場合は警告を吐いてスキップします。

よくある操作例
--------------
- 監視を 30 秒間隔で実行:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード用 Execution を起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（2026-04-01 〜 2026-04-11）を生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

付記
----
本 README はコードベースの docstring と実装に基づく概要です。詳細な挙動や追加オプションは各モジュール（特に run_*.py、config.py、monitoring/*.py、ai/*.py）内の docstring を参照してください。

問題・質問があれば、どの機能について知りたいかを教えてください（起動手順、環境変数、API 使用例、あるいは特定モジュールの詳細解説など）。