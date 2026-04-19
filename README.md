KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのプロジェクトです。  
主な目的は以下のとおりです。

- 発注エンジン（ExecutionEngine）による自動発注（実取引 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）による運用監視と Kill Switch
- ポートフォリオ構築・サイズ決定・リスク調整のライブラリ
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI を利用したニュース NLP（センチメント）やレジーム判定
- ペーパートレード検証レポートなどのユーティリティ

主な特徴
--------
- 環境別分離:
  - KABUSYS_ENV によって development / paper_trading / live を選択可能
  - paper_trading モードでは MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）に記録して本番 DB と分離
- 監視と自動停止:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る KillSwitch
- ロギング:
  - 統一的な logging 設定（コンソール + 日次ローテーションファイル）
  - デフォルト log ディレクトリ: logs/
- リサーチ:
  - DuckDB を用いたファクター計算 (momentum, volatility, value)
  - 将来リターン・IC 計算などの統計ユーティリティ
- AI 機能:
  - ニュース記事を OpenAI でスコアリングし ai_scores テーブルへ登録
  - マクロニュース + MA200 に基づく市場レジーム判定（LLM を利用）

セットアップ
-----------
1. リポジトリをクローン
   - git clone <repo_url>
   - ここではソースが src/kabusys 配下にあることを想定

2. Python 環境
   - 推奨: Python 3.10+（コードは型ヒント等を使用）
   - 仮想環境を作成:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 追加で必要なパッケージがあれば追記してください（requirements.txt がある場合はそれを使用）

4. .env の作成
   - 対話式ウィザードを実行して .env を作成できます:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で作成
   - 自動ロード: .env/.env.local は Settings モジュール起動時に自動でロードされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J‑Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution 環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

設定検証
--------
.env や config/*.yaml の基本チェックを行うツールがあります。

- 実行:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

使い方（主要なスクリプト）
-------------------------

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) で失敗扱い

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB を利用
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag が作成されると安全に停止を試みる
    - 実行中の PID 管理ファイル: data/execution.pid

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用（環境に依存せず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI / 研究機能（モジュール関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクト（duckdb.connect(...)）を受け取り、DB 内テーブルを参照・更新します

運用上のファイル / フラグ
------------------------
- data/stop_requested.flag
  - run_execution 及び run_monitoring が監視している「外部からの停止要求」ファイルです。存在すると該当プロセスは停止に向かいます。

- data/kill.flag
  - KillSwitch（監視側）が重大なリスク条件を検出した際に作成するフラグです。ExecutionEngine はこのファイルの存在を検知して安全停止します。
  - Settings.kill_flag_clear_on_start を 1 に設定すると起動時に自動でクリアされます（本番環境では推奨しません）。

- data/execution.pid
  - ExecutionEngine の PID 管理ファイル

ログ
----
- デフォルトでは logs/ 以下にアプリ名ごとのログファイルが作成されます（例: logs/execution.log, logs/monitoring.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理され、コンソール（stdout）と日次ローテーションファイルを持ちます。
- ログレベルは LOG_LEVEL 環境変数または引数で設定可能。

注意事項 / 運用のヒント
---------------------
- paper_trading モードは本番 DB と分離されています。テスト実行で本番データを上書きしないよう DB パスに注意してください。
- OpenAI を使う機能は API キーが必要です。キー未設定時は ValueError が投げられる関数があります。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意書きがあります）。
- 自動環境変数ロードは Settings モジュールがプロジェクトルート（.git または pyproject.toml）を検出できる場合に実行されます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視・発注ロジックはデータ鮮度やプロセスの存続性を重視する設計になっていますが、実運用前に必ずステージングで十分にテストしてください。

ディレクトリ構成（主なファイル）
------------------------------
以下は主要なサブモジュールと代表ファイルです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト

  - execution/
    - execution_engine.py     — メイン発注ロジック（Engine）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
    - ...（実際の実装に依存）

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
    - ...（ユーティリティ群）

依存パッケージ（主なもの）
------------------------
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証に任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

開発・貢献
----------
- コードスタイル、テスト、CI 設定はプロジェクトポリシーに従って追加してください。
- 機密情報（API トークン等）は .env に入れて管理し、リポジトリへコミットしないでください。

付録: よく使うコマンド例
----------------------
- .env ウィザード
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 発注エンジン起動
  - python -m kabusys.run_execution

- 監視起動（ポーリング間隔を 30 秒にする例）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README は提供されたコードベースを基に作成しています。実際の運用・デプロイ時には config/*.yaml（存在する場合）やドキュメント、テストを参照のうえ、十分な検証を行ってください。質問や追加のドキュメント化が必要であれば教えてください。