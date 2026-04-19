README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークの一部です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine 起動スクリプト（発注ロジック、リスク管理、ブローカークライアントの組み立て）
- Monitoring（システム/発注/リスク監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量探索、リサーチユーティリティ）
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算）
- AI 関連モジュール（ニュース NLP、市場レジーム判定）
- 実行/検証補助ツール（.env ウィザード、設定検証、Paper Trading レポート）

目的は「自動売買の運用に必要な監視・リスク保護・研究ツール」を統合的に提供することです。

主な機能
--------
- ExecutionEngine の起動/実行（paper_trading モードをサポート）
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor）とアラート発行の統合
- Kill Switch：重大リスク（例：ドローダウン過大・ポジション上限超過）でエンジン停止フラグを出す仕組み
- .env 対話式ウィザード（config_setup）と設定検証 CLI（validate_config）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- DuckDB を用いたファクター計算・リサーチ（momentum/volatility/value など）
- OpenAI を使ったニュースセンチメント評価・市場レジーム判定（AI モジュール）
- ログ設定ユーティリティ（console + 日次ローテートファイル）

前提（依存ライブラリ）
--------------------
少なくとも以下を想定しています（環境により追加が必要）:

- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の検証時に任意で必要）
- sqlite3（標準ライブラリ）

インストール例（仮）
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 依存インストール（プロジェクトに requirements.txt があればそれを利用）:
  pip install duckdb psutil openai pyyaml

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. .env を作成する
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照して必要な環境変数を設定）。
   - 自動ロード: config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
4. 設定を検証する:
   python -m kabusys.validate_config
   必要なら厳格モード:
   python -m kabusys.validate_config --strict
5. データディレクトリ（デフォルト: data/）やログディレクトリ（デフォルト: logs/）の作成は多くの場合自動で行われますが、権限やパスを事前に確認してください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し別 DB（data/paper_trading.db）へ記録します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の fill モード: instant|partial|never|reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API を使用する機能で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（開発用。0/1）

実行方法
-------
- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  python -m kabusys.run_monitoring
  オプション:
    MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  備考:
    run_monitoring は KABUSYS_ENV に関係なく production sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
    停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了します。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  備考:
    KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。本番と DB を分離します。
    実行中に停止させるには data/stop_requested.flag を作成してください。ExecutionEngine 用 PID ファイルは data/execution.pid（デフォルト）に書かれます。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチモジュール
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime などの関数は DuckDB 接続を受け取り、OpenAI キーが必要です（環境変数 OPENAI_API_KEY または引数で指定）。

停止・Kill Switch
----------------
- 停止フラグ:
  - run_monitoring/run_execution はプロジェクトルート/data/stop_requested.flag の存在をチェックして安全に停止します。
- Kill Switch:
  - RiskMonitor 等の判定で危険が検出されると data/kill.flag を書き込み、ExecutionEngine 停止を促す仕組みがあります（KillSwitch）。
  - 本番で自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は危険なため注意。

ログ・データファイル
------------------
- ログ: デフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）。ログ出力先は LOG_DIR 環境変数で変更可。
- SQLite（監視）: data/monitoring.db（Settings.sqlite_path）
- DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
- Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

開発・デバッグのヒント
--------------------
- .env 自動読み込み: プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング: 全スクリプトは共通の setup_logging を使っており、コンソール + 日次ファイル出力で統一されています。
- テスト: ai モジュールや外部 API 呼び出しは内部で分離されており、テスト時は _call_openai_api 等をモックすることが想定されています。
- 監視 DB の初期化は init_monitoring_db で冪等に行われます。既存 DB に対してマイグレーション（列追加）も備えています。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env ロードと Settings
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py       — 監視用 SQLite 永続化層
  - system_monitor.py      — システム状態/データ鮮度監視
  - risk_monitor.py        — ドローダウン/ポジション上限監視
  - kill_switch.py         — kill.flag 制御
  - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
  - (その他 trade_monitor / alert_manager 等)
- execution/
  - (Engine, OrderManager, BrokerFactory, RiskManager 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
  - regime_detector.py     — 市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

ライセンス・注意事項
-------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も同旨の警告を出力します）。
- 本プロジェクトを本番で使用する場合は、API キーと発注リスクに十分注意してください。KABUSYS_ENV=live を利用する際は validate_config の警告を必ず確認してください。
- AI モジュールは外部 API を利用するためレイテンシ・コスト・エラー耐性を考慮して運用してください。API キーや請求に注意してください。

問い合わせ / さらに詳しい情報
---------------------------
各モジュールの詳細はソースコード中の docstring を参照してください。具体的な設計思想やアルゴリズム（PortfolioConstruction.md, StrategyModel.md など）がプロジェクトに含まれている想定です。必要であれば README に追記します。