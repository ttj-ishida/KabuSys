KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム用ライブラリ／起動スクリプト群です。
戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI（ニュースNLP / レジーム判定）、調査ユーティリティなどを含みます。

主な特徴
--------
- 環境ごとの切替（development / paper_trading / live）に対応した設定管理
- 発注エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）の起動スクリプト
- Paper Trading（モックブローカ）を用いた完全分離のテスト用 DB
- DuckDB を用いたファクター計算・リサーチ機能（prices_daily / raw_financials を想定）
- OpenAI を用いたニュースのセンチメント分析（ニュースNLP）およびマクロレジーム判定
- 監視用 SQLite DB（system_status, trade_logs, positions, risk_logs, dashboard）とリスク監視ロジック
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
- ユーティリティスクリプト: .env ウィザード、設定検証、Paper Trading 検証レポート等

必要条件（主な依存）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI機能を使う場合）
- PyYAML（config の内容チェックを行う場合に推奨）

（実際に使う際は requirements.txt 等に合わせて pip install してください。）

セットアップ手順（開発向け・簡易）
----------------------------
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手で作成（下記「主要な環境変数」参照）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでは data/ 配下のファイルを使用します（例: data/kabusys.duckdb, data/monitoring.db）。
   - 必要に応じて環境変数でパスを変更してください。

主要な環境変数（よく使うもの）
------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (ニュースNLP / レジーム判定を使う場合必須)
- KABUSYS_ENV: 開発モード ("development"), ペーパートレード ("paper_trading"), 本番 ("live")（デフォルト: development）
- PAPER_FILL_MODE: paper_trading 用の約定モード ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH（PID / kill flag 用パス）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

簡易 .env 例
-------------
（config_setup で生成される .env と同様のキーを設定してください）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

実行方法（主要スクリプト）
--------------------------
- 監視（Monitoring）プロセス起動:
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - run_monitoring は data/stop_requested.flag を検知すると安全に停止します。
    - 監視は常に本番の sqlite_path を使用して監視テーブルを初期化します（環境に依らず監視 DB を本番パスで扱う設計）。

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離します。
    - run_execution は data/stop_requested.flag を検知して Engine を停止します。実行時に data/execution.pid を使います。

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション --from / --to / --db が利用可能（例: --db data/paper_trading.db）

監視・停止・Kill Switch
-----------------------
- Kill Switch:
  - RiskMonitor → KillSwitch で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine 側で検出して停止できます。
  - KillSwitch は冪等で既存の kill.flag を上書きしません。 kill_flag_clear_on_start が有効なら起動時に kill.flag を自動クリアします（本番では無効推奨）。

- 停止フラグ:
  - run_monitoring/run_execution は data/stop_requested.flag を監視して停止動作を行います（手動停止用フラグ）。

ログ
---
- ログ出力はデフォルトで logs/ ディレクトリに日次ローテートファイル（<app_name>.log）を出力します。
- コンソール出力は stdout に出ます（cron 等でリダイレクトしやすい設計）。

主要モジュール（機能一覧）
-------------------------
- kabusys.config / settings: 環境変数の読み込み・管理、自動 .env ロード機能
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 起動前設定検証ツール
- kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト
- kabusys.run_execution: ExecutionEngine 起動スクリプト（paper_trading 切替対応）
- kabusys.utils.logging_setup: 統一ログ設定ユーティリティ
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定
- kabusys.monitoring.*:
  - monitoring_db: SQLite の監視テーブル定義・永続化層
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、PID 管理チェック
  - trade_monitor: 発注・約定に関する監視（滞留注文、異常約定等）
  - risk_monitor: ドローダウン / ポジション上限監視とリスクログ記録
  - kill_switch: Kill Switch（kill.flag）管理
  - monitoring_engine: 複数モニタを束ねるエンジン
  - alert_manager: （アラート管理。実装参照）
- kabusys.execution.*: ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerFactory（実際のブローカ実装は環境依存）
- kabusys.portfolio.*:
  - portfolio_builder: 候補選定・重み計算（等配分 / スコア加重）
  - position_sizing: 発注株数決定・集約上限・単元丸め
  - risk_adjustment: セクター上限・レジーム乗数
- kabusys.research.*:
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - feature_exploration: 前方リターン計算、IC 計算、統計サマリー
- kabusys.ai.*:
  - news_nlp: ニュース記事を OpenAI で評価して ai_scores に書き込む
  - regime_detector: ETF MA とマクロニュースを組み合わせたレジーム判定
- kabusys.tools.paper_verification_report: Paper Trading データの検証レポート生成

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイルを示した簡易ツリーです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  (実装参照)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - ...（上に記載の監視関連）
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/ (実行時に生成／利用する想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

補足・運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start=0 を強く推奨します。
- .env は機密情報（API トークン）を含むため、絶対に Git へコミットしないでください。
- OpenAI や外部 API を利用するモジュールは API 呼び出しで失敗した場合にフェイルセーフ（スキップ、既定値適用）するよう設計されていますが、重要運用時は各種再試行・監視設定を確認してください。
- DuckDB/SQLite のファイルはバックアップ・権限管理をしてください。

開発・テスト
-------------
- 単体関数群（portfolio.*、research.* 等）は副作用がなくメモリ内で動作する純粋関数群として設計されています。ユニットテストが書きやすい設計です。
- AI 関連や外部 API 呼び出しはテスト時にモックできるよう内部呼び出しをラップしています（例: _call_openai_api のパッチなど）。

ライセンスと貢献
----------------
- (ここにライセンス情報を記載してください)
- バグ報告・機能要望は Issue を立ててください。Pull Request 大歓迎です。

以上がこのコードベースの概要と使い方です。必要があれば、セットアップ用の requirements.txt や systemd / Docker の起動例、運用手順（ログローテーション、バックアップ、監視ダッシュボード統合例）などの追加ドキュメントを作成します。どの情報を優先して追加しますか？