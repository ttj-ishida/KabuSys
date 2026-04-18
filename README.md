README
======

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。
主な機能は以下のとおりです：
- 実際の発注を行う ExecutionEngine（本番／ペーパートレード切替対応）
- システム状態・注文・リスクを監視する Monitoring（ポーリングループ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP（OpenAI を用いたニュースセンチメント・市場レジーム判定）
- ペーパートレード用検証レポート生成スクリプト

特徴
----
- 環境変数 / .env による設定管理（Settings クラス）
- 本番 / ペーパートレードの DB を明確に分離（PAPER_TRADING_SQLITE_PATH）
- 設定ウィザード（対話式 .env 生成）と起動前検証 CLI
- ログは stdout と日次ローテーションファイル（logs/<app>.log）へ出力
- OpenAI（gpt-4o-mini）を使ったニューススコアリング / レジーム判定機能（API キー必要）
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等を想定）
- 監視は SQLite に永続化（monitoring.db）し監視結果やリスクイベントを記録

必要環境・依存ライブラリ
-----------------------
- Python 3.9+（typing 古い構文があるため 3.9 以上を想定）
- 主要依存:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は最低限 duckdb, psutil, openai をインストールしてください）
   - PyYAML は config 検証をしたい場合に追加: pip install pyyaml

4. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（例は下記参照）

.env の最小例
-------------
以下は実行に最低限必要な主要キーの例（実際は各値を適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
# OpenAI を使う場合:
OPENAI_API_KEY=sk-...

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行モード (development | paper_trading | live)
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 時使用）
- OPENAI_API_KEY        : OpenAI API キー（news NLP / regime 判定で必須）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/...）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒）。run_monitoring で上書き可能
- PAPER_FILL_MODE       : ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか (0/1)

設定検証
--------
起動前に設定を確認できます：
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

使い方（主要スクリプト）
-----------------------

1. 実行エンジン（ExecutionEngine）
- 本番またはペーパートレードの発注エンジンを起動します。
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB とは分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

2. 監視ループ（Monitoring）
- システム・注文・リスク監視をポーリングします。
- コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - デフォルト 60 秒間隔（MONITOR_POLL_INTERVAL 環境変数で上書き可能）
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
  - 停止は data/stop_requested.flag を作成することで行えます
  - 監視結果は SQLite（data/monitoring.db）へ保存されます

3. 環境設定ウィザード
- python -m kabusys.config_setup
  - 対話式に .env を生成・更新します

4. ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

5. その他（ライブラリ関数）
- 研究・ポートフォリオ・AI 機能はモジュールとして import して使用できます。
  例:
    from kabusys.research import calc_momentum
    from kabusys.ai.news_nlp import score_news

ログ
----
- setup_logging ユーティリティにより stdout と日次ローテートファイル（logs/<app>.log）へ出力します。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

監視・停止機構
--------------
- Kill Switch / stop flag:
  - 実行停止信号: data/kill.flag（KillSwitch）
  - 実行停止要求: data/stop_requested.flag（run_* スクリプトが検出して終了する）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリア（注意: 本番では推奨しない）

AI（OpenAI）関連
-----------------
- news_nlp（score_news）・regime_detector（score_regime）は OpenAI API（gpt-4o-mini）を使用します。
- API キーは OPENAI_API_KEY 環境変数または関数引数で渡してください。
- API 呼び出しはレート制限やエラー時にリトライロジックを持ち、失敗時はフォールバック動作を行います。

主要モジュール一覧（簡単な説明）
-------------------------------
- kabusys.config: 環境変数読み込みと Settings クラス
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリング起動スクリプト
- kabusys.monitoring.*: 監視関連（MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, AlertManager 等）
- kabusys.execution.*: 発注/オーダー管理等（ブローカーファクトリ、エンジン、リスクマネージャ等）
- kabusys.portfolio.*: 候補選定、重み計算、ポジションサイズ計算、セクター制限等
- kabusys.research.*: ファクター計算・特徴量探索（DuckDB での時系列処理）
- kabusys.ai.*: ニュース NLP（news_nlp）、市場レジーム判定（regime_detector）
- kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成

ディレクトリ構成（抜粋）
-----------------------
プロジェクトルート (src/kabusys をパッケージとして想定)

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - data/         (runtime に自動作成されることを想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB データ)
    - kill.flag / stop_requested.flag / execution.pid

運用上の注意
------------
- KABUSYS_ENV=live では実際に発注が行われる可能性があるため、設定（API パスワード・通知設定・Kill Switch 設定等）を慎重に確認してください。
- .env は機密情報（API トークン）を含むため、絶対にバージョン管理へコミットしないでください。
- ログディレクトリ・DB の保存先は設定可能ですが、ディスク容量とバックアップ方針を考慮してください。
- OpenAI API の使用はコストが発生するため、利用状況を監視してください。

トラブルシューティング
----------------------
- 設定検証でエラーが出たら: python -m kabusys.validate_config を実行し、指摘に従って .env を修正
- DB が見つからない/権限エラーが出る場合: 環境変数のパスとディレクトリの所有権/権限を確認
- OpenAI 呼び出し失敗: OPENAI_API_KEY が正しく設定されているか、ネットワークや API 制限を確認
- プロセス優先度設定に失敗する場合: psutil.AccessDenied（権限不足）であることが多い。必要であれば管理者権限で実行

付録 — よく使うコマンド例
--------------------------
- .env を生成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。プロジェクトの各モジュールは README の範囲を超える詳細な仕様（関数引数や戻り値、DB スキーマ）を docstring に記載しています。必要に応じて個別モジュールの docstring を参照してください。