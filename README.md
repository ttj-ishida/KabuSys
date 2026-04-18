KabuSys — 日本株自動売買システム
=============================

本ドキュメントはこのリポジトリの概要、主要機能、セットアップ手順、および基本的な使い方をまとめた README です。開発・ペーパートレード・本番（live）を想定した構成になっています。

要点
- Python製の自動売買システム（モジュール群は発注エンジン、監視、ポートフォリオ構築、リサーチ、AIベースのニュース解析など）
- 環境変数/.env による設定管理。自動で .env / .env.local を読み込み（無効化可）
- 実行スクリプト:
  - run_execution — ExecutionEngine（発注エンジン）
  - run_monitoring — SystemMonitor（監視ループ）
  - config_setup — .env 対話ウィザード
  - validate_config — 設定検証ツール
  - tools.paper_verification_report — ペーパートレード検証レポート生成

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム向けライブラリ／実行環境です。主な目的は以下の通りです。

- データ取得・分析（DuckDB を用いたファクター計算）
- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）
- 発注・ポジション・監視の永続化（SQLite / DuckDB）
- 監視（System / Trade / Risk）とアラート、Kill Switch（停止フラグ）
- ペーパートレード向けの分離（MockBrokerClient と専用 SQLite）
- ニュースを LLM（OpenAI）でスコアリングして投資判断に活用

主な機能一覧
--------------
- 環境設定
  - .env 対話ウィザード（kabusys.config_setup）
  - 自動読み込み（プロジェクトルートの .env/.env.local、無効化可）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV により paper_trading と live を切替）
  - run_monitoring: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - stop/kill フラグ機構（data/stop_requested.flag、data/kill.flag）
- データベース
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・トレードログ（デフォルト data/monitoring.db）、ペーパートレード専用 DB（data/paper_trading.db）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケーリング）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）統合
  - news_nlp: ニュース記事のセンチメントを LLM でスコア化し ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - 統一的なログ設定（kabusys.utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポートを生成（各種指標と PASS/FAIL 判定）

設定（環境変数）
----------------
必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 推奨設定
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

.env の自動読み込み挙動
- 起動時にプロジェクトルートを探索 (.git または pyproject.toml を基準)
- .env を先に読み込み（既存 OS 環境変数を上書きしない）
- .env.local をその後で読み込み（既存 OS 環境変数を保護しつつ上書き可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

セットアップ手順（ローカル、基本）
---------------------------------
1. Python 環境（推奨: 3.10+）を用意
2. 必要パッケージをインストール（例）
   - duckdb, psutil, openai, pyyaml（validate の YAML 検証用）, など
   - 例: pip install duckdb psutil openai pyyaml
   - 実際の requirements.txt がある場合はそれを使用してください
3. .env を用意
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に）
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）
5. 初回 DB 作成
   - run_execution / run_monitoring 実行時に必要テーブルは自動作成されます
6. 実行ユーザで data/ や logs/ ディレクトリに書き込み権限があることを確認

基本的な使い方
--------------

- ExecutionEngine を起動
  - 環境例（ペーパートレード）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading モードでは MockBrokerClient を使用し、データは paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 起動時に data/kill.flag が存在する場合はエンジンを起動しません（安全機構）。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL で間隔を指定可能（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - ログや閾値は Settings 経由（.env）でカスタマイズ可能
  - 監視は常に本番用の sqlite_path を参照（KABUSYS_ENV に依らず本番 sqlite_path）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB はデフォルト data/paper_trading.db。--db オプションで指定可能。

停止・Kill スイッチ
- 停止のためのフラグ:
  - run_scripts は data/stop_requested.flag を検知してループを終了します（主に運用での手動停止用）。
  - Kill Switch: data/kill.flag は ExecutionEngine 停止のために書き込まれる（監視がトリガーした場合等）。
- KillSwitch はリスクアラート（ドローダウン・ポジション上限等）に応じて kill.flag を書き込みます。
- 実行スクリプト側でも stop_requested.flag の有無を見て graceful に停止します。

ロギング
- 共通設定は kabusys.utils.logging_setup.setup_logging を通して行われます
- デフォルト出力:
  - コンソール (stdout)
  - 日次ローテーションファイル: logs/<app_name>.log （30 日分保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

AI（OpenAI）機能
- news_nlp と regime_detector は OpenAI API（gpt-4o-mini など）を利用します
- API キー: OPENAI_API_KEY 環境変数または各関数の api_key 引数で指定
- LLM コールはリトライ・バックオフ・レスポンスバリデーション等の保護付き
- LLM を使わない（または未設定）場合、多くの処理はフォールバック（安全側）で動作します

重要なファイル / フラグ / デフォルトパス
- data/monitoring.db           — デフォルトの監視用 SQLite（SQLITE_PATH）
- data/paper_trading.db        — ペーパートレード専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb          — DuckDB（DUCKDB_PATH）
- data/kill.flag               — Kill Switch フラグ（実行エンジン停止用）
- data/stop_requested.flag     — run_* スクリプトのグローバル停止フラグ
- data/execution.pid           — ExecutionEngine の PID（起動時に利用）
- logs/<app_name>.log          — ログ出力（例: logs/execution.log, logs/monitoring.log）

ディレクトリ構成
-----------------
主要なソース配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
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
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, Reconciler, RiskManager などの実装)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に生成される（DB/flag/pid 等。未コミット推奨）
  - logs/                      — ログ出力先（デフォルト）

（注）execution パッケージ以下の詳細実装は本 README の対象ではありますが、発注 API 固有の設定や Broker クライアント実装に依存します。環境に応じて Broker クライアントを実装／設定してください。

運用上の注意点 / ベストプラクティス
-----------------------------------
- 本番運用前に必ず python -m kabusys.validate_config で設定を確認する
- .env は機密情報を含むためリポジトリにコミットしない（config_setup でも同旨の注意文が出力されます）
- KABUSYS_ENV=live のときは kill/alert 関連の設定（LINE トークン等）を確実に設定する
- ログディレクトリや data/ に対する権限管理を正しく設定する
- OpenAI を使う場合は API キーの利用制限・料金を理解しておく

トラブルシューティング
-----------------------
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認
  - プロジェクトルートの判定は .git または pyproject.toml を探索します
- run_monitoring のポーリング間隔を変えたい:
  - MONITOR_POLL_INTERVAL 環境変数（秒）を設定（1 秒以上）
- ペーパートレードと本番 DB が混ざる心配:
  - paper_trading モードは paper_sqlite_path に記録し本番 DB とは分離されます

開発者向けメモ
----------------
- ロギング設定は kabusys.utils.logging_setup.setup_logging を各スクリプトで最初に呼んで統一しています
- プロセス優先度設定（set_process_priority("high")）を起動直後に行います。psutil による権限エラーは警告でスキップされます
- DuckDB 接続は分析処理（research / ai）で使用します。DuckDB にテーブルを用意することでリサーチ処理を動かせます

参考コマンドまとめ
------------------
- .env ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config [--strict]
- Execution 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上が本プロジェクトの README です。必要であれば、.env.example のテンプレートや具体的な systemd / Supervisor のユニット例、CI 用の簡単なテスト手順なども追加します。どの情報を追加しますか？