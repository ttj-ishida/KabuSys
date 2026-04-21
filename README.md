KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定したロジック・運用ユーティリティ群です。  
主に以下の役割を持つコンポーネントを含みます。

- ExecutionEngine（発注エンジン）起動スクリプトと実行ロジック（本番 / ペーパートレード対応）
- Monitoring（システム監視・アラート・Kill Switch）
- Portfolio 構築（候補選定、重み付け、ポジションサイズ算出）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP / レジーム判定、OpenAI を利用）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード等）
- 運用ツール（Paper Trading の検証レポート等）

主な特徴
--------
- 本番／ペーパートレード切替（KABUSYS_ENV）により DB 分離やモックブローカー利用が可能
- Monitoring は本番の監視 DB（SQLITE_PATH）を常に参照して稼働状況を記録
- Kill Switch（data/kill.flag）で実行中の ExecutionEngine を安全に停止可能
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（API キー必要）
- DuckDB を利用した研究・分析用クエリ（prices_daily / raw_financials 等を想定）
- ログは stdout と日次ローテーションファイル（logs/<app>.log）に出力

機能一覧（抜粋）
----------------
- run_execution.py: ExecutionEngine 起動（KABUSYS_ENV による挙動差分）
  - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient を利用
  - 停止フラグ（data/stop_requested.flag）検知で優雅に停止
- run_monitoring.py: SystemMonitor のポーリングループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視 DB (SQLITE_PATH) は常に本番設定を使用
- config_setup.py: .env の対話式ウィザード（初期作成 / 更新支援）
- validate_config.py: .env / config/*.yaml の静的チェック（--strict モードあり）
- monitoring/*: MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、監視 DB（monitoring_db.py）
- portfolio/*: 候補選定、重み計算、リスク調整、株数算出（単元丸め・aggregate cap 等）
- research/*: ファクター計算（momentum / value / volatility）や特徴量解析（IC 等）
- ai/*: news_nlp（ニュースセンチメント → ai_scores）、regime_detector（市場レジーム判定）
- tools/paper_verification_report.py: ペーパートレード検証レポート生成 CLI

前提・依存関係
--------------
- Python 3.10+
  - （コードで union 型表記 A | B を使用しているため 3.10 以上が必要）
- 外部ライブラリ（requirements にまとめる想定）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行う場合に必要）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてバージョンを固定して requirements.txt を作成してください）
3. 初期設定ファイル (.env) の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を手動作成
4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict
5. データディレクトリ・ログディレクトリの準備
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
     - SQLite (監視): data/monitoring.db（環境変数 SQLITE_PATH で変更可）
     - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
     - ログ: logs/（環境変数 LOG_DIR で変更可）
   - 必要なディレクトリは起動時に自動作成される場合がありますが、権限等を事前に確認してください。

重要な環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading にすると run_execution はペーパートレード専用 DB を使用しモックブローカーを利用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能（ai/news_nlp, ai/regime_detector）で必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

使い方（起動例）
----------------
- ExecutionEngine を起動（バックグラウンド起動等は環境に合わせて）
  - python -m kabusys.run_execution
  - ペーパートレード実行:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- Monitoring を起動（監視のポーリングループを開始）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
- 設定検証
  - python -m kabusys.validate_config
- .env の対話式作成
  - python -m kabusys.config_setup
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

運用上の注意
-------------
- 停止フラグ / Kill Switch
  - 実行中の停止リクエスト（運用者が手動で停止する場合など）は以下ファイルにより制御されます。
    - data/stop_requested.flag — run_execution / run_monitoring のループ監視用（存在するとループを抜ける）
    - data/kill.flag — KillSwitch が書き込むと ExecutionEngine 停止要求となる（存在チェックで再起動防止）
  - KillSwitch は RiskMonitor 等の判定で条件を満たした場合に書き込まれます。KILL_FLAG_CLEAR_ON_START の設定に注意（本番では 0 推奨）。
- DB 分離
  - Monitoring（監視）は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用します。
  - Execution は paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。
- ログ
  - setup_logging により stdout と logs/<app>.log（日次ローテート）が使われます。ログディレクトリの権限に注意してください。
- OpenAI の使用
  - ai/news_nlp, ai/regime_detector は OPENAI_API_KEY が必要。API 呼び出し時のレートやコストに注意。
  - API 失敗時はフェイルセーフが組み込まれており、致命的失敗にならないよう設計されていますが、結果の正確性は API 可用性に依存します。

ディレクトリ構成（src/kabusys の主要ファイル）
------------------------------------------
（ソースベースの抜粋構成）
- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - (ExecutionEngine, order manager/repository, broker factory 等 実装ファイル)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は実装ファイルの代表であり、さらに細かいモジュールに分かれています）

開発・拡張のヒント
------------------
- DuckDB 接続を受け取って純粋関数で計算する設計（research/*）のため、データベースを差し替えてテスト可能です。
- AI 周りは API 呼び出し部分が関数で切り出されているためモック化しやすく、ユニットテストが書きやすい構造です（例: _call_openai_api のパッチ）。
- 設定読み込みはプロジェクトルート（.git または pyproject.toml）から自動的に .env を読みます。テストから自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問い合わせ / 追加ドキュメント
--------------------------
本 README はコードベースの主要点をまとめたサマリです。各モジュール（特に ExecutionEngine、order_manager、broker_factory 等）にはそれぞれ仕様や設計ノートがあります。実運用前には以下の確認を推奨します。

- .env（機密情報）の管理方法（Git にコミットしない）
- 本番（live）起動時の通知設定（LINE トークン等）
- Kill Switch / Deadman Switch の運用ルール
- OpenAI のコスト管理（API キー・レート制限）

必要であれば、各サブモジュールの詳細ドキュメント（API、DB スキーマ、起動フロー等）を別途作成します。どの部分を詳細にしたいか教えてください。