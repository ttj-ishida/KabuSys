KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究プラットフォーム向けの小規模フレームワークです。本リポジトリには以下の主要機能が含まれます。

- 発注エンジン（ExecutionEngine）: 実取引 / ペーパートレード切替対応。
- 監視モジュール（Monitoring）: システム状態、注文ログ、リスク監視、Kill Switch。
- ポートフォリオ構築ロジック: 候補選定・重み付け・株数決定・セクター調整など。
- リサーチ機能: ファクター計算、特徴量探索、将来リターン / IC 計算。
- AI 支援モジュール: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定。
- 運用補助ツール: .env ウィザード、設定検証、ペーパートレード検証レポート等。

特徴
----
- 設定は .env / 環境変数で管理。config_setup による対話的ウィザードを提供。
- 実行環境（development / paper_trading / live）を切り替え可能。
- 監視ログは SQLite（monitoring.db）、分析は DuckDB（kabusys.duckdb）。
- OpenAI を用いたニュースセンチメント集計やレジーム判定を内蔵（APIキー必須）。
- Process priority / CPU affinity を OS に依存せず設定（psutil 使用）。
- ロギングは統一的に設定。コンソール + 日次ローテートファイル出力。

セットアップ手順
----------------
前提:
- Python 3.9+（型アノテーションの union 表記などに準拠）
- システムに sqlite3 が利用可能（標準）
- 以下の Python パッケージをインストール:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — config/*.yaml の検証に使用

例（pip）:
  pip install duckdb psutil openai PyYAML

1. リポジトリをクローン / 展開
2. プロジェクトルートに移動（pyproject.toml または .git を基準に自動検出）
3. 対話的に .env を作成:
   python -m kabusys.config_setup
   - J-Quants、kabuステーションパスワードなど必須値を入力してください。
4. 設定を検証:
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。
5. （必要に応じて）データディレクトリ作成:
   mkdir -p data logs

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill flag を自動クリア（開発用）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
--------------------

環境作成 / 検証
- 対話式 .env 作成:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

実行系
- ExecutionEngine 起動（通常はサービス/cron 等で実行）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンを安全に停止します。
  - PID ファイル: data/execution.pid（デフォルト）。Settings.pid_file_path で変更可能。

監視系
- SystemMonitor のポーリングループ起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず同じ monitoring DB を使う設計）。
  - run_monitoring / run_execution ともにプロセス優先度を "high" に設定しようとします（psutil 必須）。

ツール
- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可。
  - レポートは稼働率、注文成功率、送信率、レイテンシ等の指標を出力します。

AI 機能
- ニュース NLP スコアリング（programmatic API）:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key=...)
  - DuckDB 接続を渡して呼び出します（OpenAI API キー必須）。

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key=...)

監視・停止フラグ
- stop_requested.flag (data/stop_requested.flag)
  - run_execution・run_monitoring はこのファイルの存在を検出してループを終了します（手動停止用）。
- kill.flag (data/kill.flag)
  - KillSwitch が書き込むことで ExecutionEngine に「停止」の意思を伝えます（リスク発生時）。
  - KillSwitch は冪等にファイルを書き、既存なら上書きしません。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動的にクリアされます（本番では推奨されません）。

DB スキーマ（監視用 / 主要テーブル）
- system_status: cpu_percent, memory_percent, disk_percent, process_ok, recorded_at
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, latency_ms 等）
- positions: 保有ポジション
- risk_logs: リスクイベント（DRAWDOWN_ALERT, POSITION_LIMIT 等）
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ログ
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルトログディレクトリ: logs/）。
- コンソール出力は stdout を使用します。
- ログ設定は kabusys.utils.logging_setup.setup_logging を介して統一されています。

ディレクトリ構成（抜粋）
----------------------
以下は主要なモジュールとディレクトリの一覧（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の自動読み込みと Settings クラス
  - config_setup.py          — .env 作成ウィザード（対話式）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - (ExecutionEngine, OrderManager, RiskManager 等 — 発注ロジック)
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ （実行時に使用するファイル置き場）
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid

設計上の注意点 / ヒント
---------------------
- 設定の優先順位は OS 環境変数 > .env.local > .env です。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- run_monitoring は監視ログの初期化（init_monitoring_db）を行います。既存 DB のスキーマ変更はマイグレーション処理（カラム追加）を含む場合があります。
- ExecutionEngine は KABUSYS_ENV=paper_trading のとき paper_trading 用 SQLite に書き込み、本番 DB と分離します。実運用では本番/テスト用 DB の混同に注意してください。
- OpenAI を使う機能を運用する場合、API レート制限やエラーに対するバックオフ戦略が実装されていますが、API キーの漏えいやコスト管理には注意してください。
- PyYAML がない場合、validate_config の YAML 内容チェックはスキップされます（警告が出ます）。インストールを推奨します。

トラブルシューティング
---------------------
- DuckDB / OpenAI / psutil モジュールが import エラーになる:
  pip install duckdb openai psutil
- .env を変更したが反映されない:
  - Python プロセスは起動時に環境を読み込むため、変更後はプロセスを再起動してください。
  - 自動読み込みを無効にしている場合は .env を手動で export するか KABUSYS_DISABLE_AUTO_ENV_LOAD を見直してください。
- kill.flag / stop_requested.flag の削除:
  rm data/kill.flag
  rm data/stop_requested.flag
  ただし、本番環境では必ず意図を確認の上で操作してください。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献フローを記載してください。リポジトリに LICENSE ファイルがある場合は参照を追加してください。）

以上が KabuSys の開発者向け README の日本語版サマリです。リポジトリ内の各モジュールの docstring に詳細な設計・注意点が記載されていますので、実装・運用時はそちらも参照してください。必要であればコマンド例や環境変数の .env.example 生成例も追加します。