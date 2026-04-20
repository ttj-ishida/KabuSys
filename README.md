KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
ここに含まれるモジュールは、戦略開発（ファクター計算・特徴量解析）、ポートフォリオ構築、発注エンジン、監視・アラート、AI ベースのニュース NLP などを想定したユーティリティ群を提供します。

主な特徴
--------
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リスク調整（セクターキャップ、レジーム乗数）
- 発注・実行フレームワーク（ExecutionEngine を起動して注文を管理）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- 設定ウィザード（.env 対話式作成）と設定検証 CLI
- Paper Trading 向けの分離された DB をサポート
- DuckDB を用いたリサーチ / ファクター計算（prices_daily / raw_financials を利用）
- OpenAI を用いたニュース NLP、レジーム判定のサポート
- ログの一元化（コンソール + 日次ローテーションファイル）

必須外部依存（例）
-----------------
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイル検証を完全に行う場合）

セットアップ
-----------
1. リポジトリをクローンして、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストールします（環境に合わせて）。
   - 例:
     - pip install duckdb psutil openai pyyaml

3. 初期環境変数ファイルを作成します。
   - 対話ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成してください。

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

重要な環境変数（デフォルト / 意味）
-----------------------------------
（主なものを抜粋）

- KABUSYS_ENV: 実行環境。["development" | "paper_trading" | "live"]（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（default: INFO）
- OPENAI_API_KEY: OpenAI を使う機能の API キー（AI 機能利用時必須）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant|partial|never|reject、default: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、default: 0）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、default: 60）

よく使うファイル・フラグ（パスのデフォルト）
--------------------------------------------
- logs/<app_name>.log : ログファイル（setup_logging による日次ローテーション）
- data/stop_requested.flag : run_execution/run_monitoring が検知する停止フラグ
- data/kill.flag : KillSwitch が書き込む実行停止要求（ExecutionEngine に通知）
- data/execution.pid : ExecutionEngine が書き込む PID ファイル
- data/monitoring.db : 監視用 SQLite DB（SQLITE_PATH）
- data/paper_trading.db : Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb : DuckDB（DUCKDB_PATH）

使い方（コマンド、主要スクリプト）
---------------------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（.env および config/*.yaml の簡易チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db に記録する（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に stop フラグを検出したら Engine.stop() を呼んで終了
    - PID ファイルを data/execution.pid に書きます

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルト 60 秒間隔で監視を実行（MONITOR_POLL_INTERVAL で上書き可能）
    - 監視は environment に関わらず本番用 sqlite_path を使用して監視テーブルを初期化
    - data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / ニュース NLP（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止 / Kill
-----------
- 実行中プロセスを外部から安全に停止したい場合:
  - data/stop_requested.flag を作成（任意の内容を書いて良い）
    - run_execution と run_monitoring はこのフラグを検知して終了します
- Kill Switch（監視側が発動）
  - リスク条件等で KillSwitch が data/kill.flag を書き込みます（ExecutionEngine は起動時に kill.flag を確認）
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアを無効）

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で一律設定されます。
  - コンソール（stdout）出力 + 日次ローテーションファイル（logs/<app>.log）
  - ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/

注意・実装上のポイント
--------------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 設定の厳密チェック:
  - validate_config は .env の必須項目や DB パス、config ディレクトリ内の YAML ファイル（PyYAML があればパース検証）等をチェックします。
- Paper Trading は本番 DB と分離されます（paper_sqlite_path を使用）。
- OpenAI 呼び出しは耐障害設計（リトライや部分失敗フォールバック）を意識していますが、API キー管理とコストには注意してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定取得ラッパー（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
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

運用上のチェックリスト（簡易）
-----------------------------
- .env を用意し必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定したか？
- LOG_DIR / logs ディレクトリの書き込み権限はあるか？
- DuckDB / SQLite DB のパスは正しいか（親ディレクトリは存在するか）？
- OpenAI を使う場合、OPENAI_API_KEY を安全に管理しているか？
- 本番環境では KABUSYS_ENV=live として各種設定（LINE 通知等）を再確認する

ライセンス・貢献
----------------
- 本 README ではライセンス情報は含めていません。実プロジェクトでは LICENSE をプロジェクトルートに置いてください。

問い合わせ
----------
- 実装や利用に関する質問はリポジトリの Issues や担当者にお問い合わせください。

以上が本コードベースの概要と使い方のまとめです。運用やデプロイ方法は環境や要件に合わせて適宜補足してください。