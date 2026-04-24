# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。  
本リポジトリは以下の主要機能を持ち、実運用（live）・ペーパートレード（paper_trading）・開発（development）で動作を切り替えられる設計です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境ファイル作成（対話式ウィザード）
  - 設定検証
  - ExecutionEngine（発注エンジン）の起動
  - Monitoring（監視）の起動
  - Paper Trading 検証レポートの生成
  - AI系機能の実行（ニュース NLP / レジーム判定）
- 主要環境変数
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。
- 発注エンジン（ExecutionEngine）、監視エンジン（MonitoringEngine）、ポートフォリオ構築・ポジションサイズ計算、ファクター算出・リサーチ、ニュースを使った AI スコアリング等の機能を備えます。
- データ永続化に SQLite（監視・トレードログ等）および DuckDB（分析・リサーチ用）を使用します。
- 実運用（live）とペーパートレード（paper_trading）でデータベースやブローカークライアントが分離されるよう設計されています。

---

機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor をポーリングする監視プロセス起動
- 設定管理
  - config.py: 環境変数/.env の読み込み、Settings クラス
  - config_setup.py: .env を対話式で作成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の検証 CLI
- 監視（monitoring）
  - monitoring_db.py: SQLite に監視用テーブルを作成・読み書き
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager 等
  - kill flag による ExecutionEngine 停止（data/kill.flag）
- 発注（execution）
  - ExecutionEngine、OrderManager、OrderRepository、BrokerClientFactory、RiskManager、Reconciler 等（実装は別ファイル）
  - paper_trading モードでは MockBrokerClient を利用して data/paper_trading.db へ記録
- ポートフォリオ構築（portfolio）
  - 候補選定、等重／スコア重み、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- リサーチ（research）
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリ
- AI 関連（ai）
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコア付与 → ai_scores テーブルへ保存
  - regime_detector: ETF とマクロニュースを組合せて日次の市場レジーム判定、market_regime テーブルへ書き込み
- ユーティリティ
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

セットアップ手順（ローカル実行想定）
1. システム要件
   - Python 3.9+
   - SQLite（Python 標準ライブラリで利用可能）
   - 推奨 Python パッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config で YAML 検証を行う場合）
   - 例（仮の requirements がないため手動インストールの例）:
     pip install duckdb psutil openai PyYAML

2. リポジトリをクローンして仮想環境を用意
   - git clone ...  
   - python -m venv .venv && source .venv/bin/activate

3. .env の初期作成（対話式）
   - 対話式ウィザードを使い .env を作成:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成

4. 設定検証
   - 作成した .env や config/*.yaml を検証:
     python -m kabusys.validate_config
   - 警告も FAIL としたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ・ログディレクトリ
   - デフォルト SQLite / DuckDB / ログディレクトリは .env 内の設定か下記のデフォルトを使用します:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading モード)
     - LOG_DIR: logs/
   - 必要なら事前にディレクトリを作成（通常は自動作成されます）

注意: OpenAI API を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定してください。

---

使い方 — 主要コマンド・スクリプト

1) 環境ファイル作成（対話式）
- .env を対話式に作成・更新:
  python -m kabusys.config_setup

2) 設定検証
- 設定の簡易検証:
  python -m kabusys.validate_config
- --strict を付けると警告があると exit(1) で失敗扱いになります:
  python -m kabusys.validate_config --strict

3) ExecutionEngine の起動（発注エンジン）
- 実行:
  python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV により paper_trading / live / development を切替
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
  - 起動時に process priority を "high" に設定（可能な場合）
  - 停止は data/stop_requested.flag を作成するか、ExecutionEngine の kill flag（data/kill.flag）を使う
  - 起動中は PID ファイル（デフォルト data/execution.pid）を書きます

4) Monitoring の起動（監視プロセス）
- 実行:
  python -m kabusys.run_monitoring
- 挙動:
  - SystemMonitor をポーリングして system_status 等を SQLite へ記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず本番監視 DB を使用）
  - stop_requested.flag を検知するとループを終了してクリーンアップします

5) Paper Trading 検証レポートの生成
- データベース（paper_trading）の検証レポートを出力:
  python -m kabusys.tools.paper_verification_report
- 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6) AI 機能（ニュース NLP・レジーム判定）
- ニュースセンチメント（プログラムから呼ぶ例）:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="...")  # duckdb 接続を渡して使用
- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

注意: AI 機能は OpenAI API（OPENAI_API_KEY）を必要とします。API の失敗は多くの箇所でフェイルセーフ（0.0 にフォールバック等）として扱われますが、API キーは必須です。

---

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 本番での kill.flag 自動クリア（0/1）

config_setup や README に記載の .env の項目を参照してください。

---

Kill / Stop フラグについて
- data/kill.flag: Kill Switch により ExecutionEngine を停止するためのフラグ。KillSwitch が書き込みます。
- data/stop_requested.flag: run_execution.py や run_monitoring.py が監視している「直ちに終了する」ためのフラグ（外部ツールや運用者が作成して停止を促す用途）。
- ExecutionEngine 起動時、KILL_FLAG_CLEAR_ON_START=1 の場合は kill.flag をクリアするような動作をする設定が可能（本番では注意）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — Settings / .env 自動読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
    - alert_manager.py (参照)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用する DB / フラグファイル等を格納する想定ディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag / stop_requested.flag
  - logs/ (ログファイル: logs/execution.log, logs/monitoring.log など)

---

実運用上の注意
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください（config_setup も注意喚起を表示します）。
- KABUSYS_ENV=live のときは特に LINE 通知設定や kill flag の取り扱い等を厳重に確認してください（validate_config にてガードがあります）。
- OpenAI を使う処理は API コスト・レート制限・プライバシーに注意して運用してください。リトライ・バックオフが組み込まれていますが、運用設計は必須です。

---

開発者向けメモ
- ログ設定: kabusys.utils.logging_setup.setup_logging を各起動スクリプトの先頭で呼んで統一的なログ出力を行います。デフォルトは stdout + 日次ローテートファイル（logs/<app>.log）。
- SQLite 用のスキーマ作成は init_monitoring_db(SQLiteConnection) で自動化されています（冪等）。
- DuckDB は分析向けに使用。research や AI 用のテーブル（prices_daily / raw_financials / raw_news 等）を前提にしています。
- ペーパートレードでは production DB と切り離して PAPER_TRADING_SQLITE_PATH を使用するためデータ混同の心配がありません。

---

README は以上です。追加で「デプロイ / systemdユニット定義」や「CI / テストの実行方法」などのドキュメントが必要であれば、実行環境や運用ポリシーに応じた例を追記できます。