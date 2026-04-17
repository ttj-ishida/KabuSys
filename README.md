# KabuSys (README)

以下は本リポジトリ（src/kabusys）に含まれる自動売買・研究・監視ユーティリティ群の概要および利用手順です。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 環境変数（主なもの）
- 使い方（コマンド例）
- 監視 / 停止フローについて
- ディレクトリ構成（概略）

---

プロジェクト概要
- KabuSys は日本株を対象とした自動売買システムのライブラリ／ユーティリティ群です。
- 発注エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築、リサーチ（ファクター計算、特徴量解析）、AI（ニュース NLP / レジーム判定）周りのモジュールを含みます。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切り替え可能です。

主な機能一覧
- Execution
  - 実際のブローカークライアント（kabuステーション）または MockBrokerClient による注文実行（KABUSYS_ENV に依存）
  - 注文管理、リコンシリエーション、リスク管理（RiskManager）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor の組合せによる定期監視
  - 監視ログを SQLite（monitoring.db）に永続化（MonitoringDB）
  - KillSwitch による停止フラグの自動生成、LINE 通知（AlertManager）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースのセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF ma200 とマクロニュースを組合せた市場レジーム判定
- ツール
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレード DB に対する検証レポート生成

前提条件 / 依存パッケージ
- 推奨 Python バージョン: 3.10+
- 必須（主要）パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - requests
- 任意（検証用）:
  - PyYAML（config/*.yaml の検証に使用）
- インストール例:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai requests PyYAML

セットアップ手順
1. リポジトリをクローンしてプロジェクトルートに移動
   - git clone ... ; cd <repo>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML
4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成（.env は絶対に Git にコミットしないこと）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます
6. データディレクトリ初期化
   - デフォルトでは data/ 以下に SQLite/DuckDB が作られる想定です。必要に応じてディレクトリを作成してください。

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に書き込む
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)  — Monitoring は常に本番 sqlite_path を使用
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB（本番 DB と分離）
- その他
  - LOG_LEVEL (default: INFO)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
  - OPENAI_API_KEY（AI モジュール用）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き。デフォルト 60）

使い方（主な実行例）
- 環境セットアップ・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- ExecutionEngine の起動（注文実行）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使います
    - 実行中、data/execution.pid が書かれます
    - 停止させたい場合は data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書きます
- Monitoring の起動（監視ループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト間隔は 60 秒。MONITOR_POLL_INTERVAL で上書き可能（1 秒以上）
    - 監視は Settings.sqlite_path（monitoring.db）を使用します（環境に依らず本番パス）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI / レジーム関連（ライブラリ的に利用）
  - DuckDB 接続を作成してインポートする例:
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date=datetime.date(2026,4,1), api_key="...")  # または OPENAI_API_KEY 環境変数
  - レジーム
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date=..., api_key=...)
  - これらはコマンドライン用エントリポイントは用意されていないため、スクリプトや cron / Airflow などから呼び出して使います。

監視 / 停止フローについて（重要）
- run_execution には以下のファイル/フラグが使用されます（プロジェクト data ディレクトリ内）
  - data/execution.pid: 起動時に PID が書かれる（SystemMonitor が参照）
  - data/stop_requested.flag: 外部からこのファイルが存在すると run_execution は起動せず、稼働中は停止処理に入る
  - data/kill.flag: KillSwitch により書き込まれると ExecutionEngine を停止するための信号。KILL_FLAG_CLEAR_ON_START により起動時に自動クリアする設定がある
- run_monitoring は stop_requested.flag を参照して自ら終了します（停止フラグを検知すると監視ループを抜ける）
- Monitoring による KillSwitch（条件: ドローダウン超過、ポジション上限超過など）がトリガーされると data/kill.flag を書き、AlertManager 経由で LINE 通知を送る（設定がある場合）

その他のポイント・挙動
- DB マイグレーション: monitoring_db.init_monitoring_db() は何度でも呼べる冪等設計で、必要なカラムがなければ追加する簡易マイグレーションを行います（例: trade_logs.latency_ms、dashboard.peak_value 追加処理）
- Paper trading は本番 SQLite DB と完全に分離されるように設計されています（settings.is_paper に応じて paper_sqlite_path を使用）
- process priority: 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil による優先度変更。権限がない場合は警告を出してスキップ）
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。0 以下や不正値の場合はデフォルトにフォールバック

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py: パッケージ定義（__version__ 等）
  - config.py: 環境変数・設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py: SQLite を使った監視ログ永続化層（init / MonitoringDB）
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 注文滞留・約定異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - alert_manager.py: LINE Push 通知ユーティリティ
    - kill_switch.py: kill.flag 書き込みユーティリティ
  - execution/ (発注・注文管理関連。外部ブローカー実装は別モジュール)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など（起動スクリプトから使用）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py: ポートフォリオ構築ロジック（純粋関数群）
  - research/
    - factor_research.py, feature_exploration.py: DuckDB を用いたファクター計算 / 解析
  - ai/
    - news_nlp.py: ニュースセンチメント (OpenAI)
    - regime_detector.py: 市場レジーム判定（ma200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
  - utils/
    - process_priority.py: psutil ベースの優先度 / CPU affinity 設定ユーティリティ

最後に（運用上の注意）
- .env は機密情報を含むため絶対にバージョン管理に含めないでください。
- KABUSYS_ENV=live での運用はリスクが高いため、validate_config で警告を確認し、LINE 通知など監視が整っていることを確認してください。
- OpenAI（AI）機能を運用で使う場合は API コストとレイテンシ、エラー時のフォールバック設計（本実装ではエラー時にスコア 0 などで続行する）を十分に理解してください。
- DB（DuckDB / SQLite）のバックアップと運用監視を行ってください（ディスク容量監視も重要です）。

質問や README の追加要望（例: 実行フロー図、より詳細な設定例、systemd / Docker 化手順など）があれば教えてください。必要に応じて追記します。