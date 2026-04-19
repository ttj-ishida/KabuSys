KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ群／スクリプト群です。  
バックエンドの監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、ファクター計算、ニュース NLP によるセンチメント評価などの機能を含みます。  
このリポジトリはライブラリとしてのモジュール群と、起動用の CLI スクリプト群（実行エンジン／監視ループ／設定ウィザード／検証ツール／レポート生成）を提供します。

主な機能
--------
- ExecutionEngine 起動（run_execution）
  - KABUSYS_ENV に応じて paper_trading（MockBroker）と live を切替
  - paper_trading 用の独立した SQLite DB をサポート（デフォルト: data/paper_trading.db）
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応
- Monitoring（run_monitoring / MonitoringEngine）
  - システム状態（CPU/Mem/Disk）監視、プロセス生存確認、データ鮮度チェック
  - 取引・リスクの監視（滞留注文・約定異常・ドローダウン監視等）
  - Kill Switch（kill.flag）を用いた ExecutionEngine 停止信号
  - 監視ログの永続化（SQLite）
- Portfolio construction
  - 候補選定、等重・スコア重み、リスクベースの株数算出、セクターキャップなど
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）
  - 将来リターン / IC / 統計サマリ等のユーティリティ
- AI 関連
  - ニュース記事を OpenAI に投げて銘柄別センチメントを算出・保存（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - 対話式 .env 設定ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（型ヒントの union 表記等を使用）
- SQLite（標準ライブラリ）、DuckDB（Python パッケージ）
- ネットワーク経由の機能を使う場合は OpenAI API キーなどが必要

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最小例）
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

.env（環境変数）設定
- 推奨フロー: 対話式ウィザードで作成
  - python -m kabusys.config_setup
- 主要な必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_station_password
- 主要な任意 / 既定値
  - KABUSYS_ENV=development  # development | paper_trading | live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=（AI 機能使用時に必要）
- 自動ロード
  - プロジェクトルートにある .env / .env.local は自動で読み込まれます（OS 環境変数を上書きしません）
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

設定検証
- 起動前に設定をチェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

使い方（主要コマンド）
--------------------

1) Execution Engine を起動
- 実行（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
- ペーパートレードで起動したい場合:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパーでは MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます
- 停止方法:
  - data/stop_requested.flag を作成すると起動中のループは検知して停止します
  - Kill Switch（kill.flag）により ExecutionEngine 停止を促す設計もあり（詳細は monitoring モジュール参照）

2) Monitoring を起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止フラグファイル:
  - data/stop_requested.flag を作成するとループを終了します

3) .env 作成 / 更新（ウィザード）
- python -m kabusys.config_setup

4) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告をエラー扱いします

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。 --db で別パス指定可、または環境変数 PAPER_TRADING_SQLITE_PATH を使用

6) AI（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
- モジュール関数を直接呼び出して処理する想定:
  - 例（Python REPL / スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ・PID・フラグファイル
-----------------------
- ログ:
  - defaults: logs/<app_name>.log に日次ローテーションで保存（TimedRotatingFileHandler）
  - コンソールは stdout に出力
- PID / フラグ:
  - 実行用 PID: data/execution.pid（Settings.pid_file_path、デフォルト）
  - Stop flag (run scripts 停止): data/stop_requested.flag
  - Kill Switch flag: data/kill.flag（Settings.kill_flag_path、デフォルト）
- DB:
  - Monitoring DB（SQLite、デフォルト）: data/monitoring.db
  - DuckDB（分析用、デフォルト）: data/kabusys.duckdb

環境変数まとめ（主要）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DB / ファイルパス
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - PID_FILE_PATH (execution.pid パス)
  - KILL_FLAG_PATH (kill.flag パス)
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector 等で必要）
- 監視ループ間隔
  - MONITOR_POLL_INTERVAL（秒。run_monitoring で使用）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py            — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py            —（取引監視: ファイルに含まれる想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            —（アラート連携のための実装想定）
  - execution/
    - execution_engine.py         — ExecutionEngine（本体）
    - broker_factory.py           — Broker クライアント生成
    - order_manager.py
    - order_repository.py
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

設計上の注意点 / 備考
--------------------
- 環境分離
  - paper_trading モードは本番 DB と分離して専用の PAPER_TRADING_SQLITE_PATH を使用します（安全対策）。
- フェイルセーフ
  - AI API 呼び出しや外部依存はリトライ／フォールバックを伴う設計。失敗時には処理をスキップしてシステム全体の継続を優先します。
- 自動ロード
  - プロジェクトルートの .env / .env.local を自動で読み込みます。別途環境での上書きや保護が可能です。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成とカラム追加を行います。
- ログディレクトリ作成に失敗した場合はファイルログを諦めてコンソール出力のみで継続します。

サンプル .env（最小例）
---------------------
# KabuSys 環境変数（例）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-....

開発・デバッグのヒント
---------------------
- ログの詳細度を上げたい場合は LOG_LEVEL=DEBUG を設定してください。
- モジュール単位の実行は Python の -m 形式で行えます（例: python -m kabusys.tools.paper_verification_report）。
- duckdb 接続は多くのリサーチ関数で直接受け取る設計なので、スクリプトや REPL で duckdb.connect(...) を作って渡すことで動作確認できます。

貢献 / 拡張ポイント
-------------------
- ブローカークライアントのプラグイン（実取引側の拡張）
- strategy / execution のテスト・シミュレーションスイート
- GUI / ダッシュボード連携（ダッシュボード更新ロジックは monitoring_db にある）
- 単体テストと CI（validate_config の自動チェックなど）

ライセンス
----------
このリポジトリのライセンス表記がない場合は、使用前にライセンスを明示してください。

お問い合わせ
------------
実行や設定で不明点があれば、リポジトリの README を更新するか、プロジェクト内のドキュメント（PortfolioConstruction.md 等）に目を通してください。追加の使用例や運用手順が必要であれば、目的に応じたサンプルやデプロイ手順を追記できます。