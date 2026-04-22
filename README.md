README
======

このリポジトリは「KabuSys」— 日本株の自動売買・リサーチ用フレームワークの一部実装です。以下にプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システムおよび研究ツール群を含む Python パッケージです。本実装は以下の領域をカバーします:

- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した発注管理、レコンシリエーション、リスク管理
- 監視コンポーネント（Monitoring）: システム稼働・発注ログ・リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数
- リサーチ（Research）: ファクター計算、特徴量探索（IC 等）
- AI 支援モジュール（AI）: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ツール類: .env 対話ウィザード、設定検証 CLI、Paper Trading 検証レポート
- ユーティリティ: ロギング設定、プロセス優先度設定、DB 初期化等

主な設計方針:
- データベースは SQLite（監視・ペーパートレード）および DuckDB（分析）を利用
- 環境変数ベースの設定（.env をサポート）。自動ロード機能あり
- 本番（live）・ペーパー（paper_trading）・開発（development）を明確に分離
- LLM 呼び出しはフェイルセーフ（API 失敗でも例外を投げず継続する設計が多い）

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 設定管理 / 支援
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
- 監視
  - monitoring_db.py: 監視 DB（SQLite）テーブルの初期化・永続化ロジック
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager 等
- ポートフォリオ構築
  - portfolio_builder.py: 候補選定・重み計算（等重み / スコア加重）
  - position_sizing.py: 発注株数計算（risk_based, equal, score）
  - risk_adjustment.py: セクターキャップ、レジーム乗数
- リサーチ
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ
- AI（OpenAI）
  - news_nlp.py: ニュース記事から銘柄別センチメントスコアを生成して ai_scores に書き込み
  - regime_detector.py: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率、成功率、レイテンシ等）
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定
  - config.py: 環境変数の読み込み・検証（自動 .env ロード、Settings クラス）

セットアップ手順
----------------
前提:
- Python 3.9 以上（実装の型注釈・モジュールに依存）
- システムにより追加のネイティブ依存がある場合あり（psutil など）

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   必須（代表例）:
     pip install duckdb psutil openai
   オプション:
     pip install PyYAML  # validate_config.py が YAML 検証を行う場合

   （本リポジトリに requirements.txt があればそれを使用してください:
    pip install -r requirements.txt）

4. データディレクトリの準備:
   多くのモジュールはデフォルトで data/ や logs/ に書き込みます。通常は自動作成されますが、念のため:
     mkdir -p data logs

5. .env の作成:
   対話式ウィザードを使う:
     python -m kabusys.config_setup
   あるいは .env を手動で作成（例は下記）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（KABUSYS_ENV=paper_trading）
- DUCKDB_PATH: DuckDB ファイル（分析用、デフォルト: data/kabusys.duckdb）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

例 .env（抜粋）
----------------
# .env（例）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方
------
各スクリプトはモジュールとして実行できます（推奨: プロジェクトルートで実行）。

1. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

2. 実行エンジンを起動
   - 通常（環境に応じて .env で KABUSYS_ENV を設定）
     python -m kabusys.run_execution
   - ペーパートレードでは別 DB に記録され、本番 DB と分離されます（KABUSYS_ENV=paper_trading）。

   実行挙動:
   - 実行時に data/execution.pid に PID を書き、停止は data/stop_requested.flag / data/kill.flag によって制御されます。

3. 監視プロセスを起動
   python -m kabusys.run_monitoring
   オプション（環境変数）:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   注意:
   - run_monitoring は KABUSYS_ENV に関わらず「本番」用 sqlite_path を使用して監視ログを書きます（監視は本番 DB を参照する前提）。

4. .env ウィザード（対話式）
   python -m kabusys.config_setup

5. Paper Trading 検証レポート
   python -m kabusys.tools.paper_verification_report
   期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   DB 指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI モジュールを利用する場合
   - 環境変数 OPENAI_API_KEY を設定してください。
   - news_nlp.score_news(conn, target_date) / regime_detector.score_regime(conn, target_date) として DuckDB コネクション経由で呼び出します（エントリポイントの CLI はありません）。

停止・Kill Switch
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution 停止に使用されるフラグ（存在を検知するとループを抜ける）
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に停止を促すために監視側が書き込みます。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成
----------------
以下は主要なファイル・ディレクトリとその概要です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、自動 .env ロード、Settings クラス
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 発注周りの実装（ブローカー抽象化、Engine 本体等）
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成・マイグレーション、MonitoringDB クラス
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py
  - research/
    - factor_research.py, feature_exploration.py, __init__.py
  - ai/
    - news_nlp.py, regime_detector.py, __init__.py
  - data/  (実行時に生成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / ヒント
-----------------
- DuckDB / SQLite ファイルパスやログディレクトリは環境変数で上書き可能です（DUCKDB_PATH, SQLITE_PATH, LOG_DIR）。
- validate_config の YAML 検証は PyYAML に依存します。インストールしていない場合は YAML 検証をスキップして警告が出ます。
- AI モジュール（news_nlp / regime_detector）は OpenAI API を利用します。API キーの管理には注意してください（.env は Git にコミットしないこと）。
- run_monitoring の MONITOR_POLL_INTERVAL は秒数を整数で指定します。不正値はデフォルト (60s) にフォールバックします。
- Process priority / CPU affinity 設定は psutil を使います。権限や OS の違いで設定に失敗する場合があります（ログは警告で出力）。

ライセンス・貢献
----------------
- 本ドキュメントにはライセンス情報を含めていません。リポジトリの LICENSE を参照してください。
- バグ報告・改善提案は Issue を通してください。

補足
----
この README はリポジトリ内のコード（src/kabusys 以下）に基づいて作成しています。実際の運用に際しては、環境変数や DB パス、ブローカー接続設定、API キー等を適切に設定し、まずは開発/ペーパートレード環境で動作確認を行ってください。