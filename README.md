# KabuSys

日本株自動売買システム（簡易説明書）

このリポジトリは、株価データの研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、および運用監視（Monitoring）を含む自動売買システムのコードベースです。用途に応じて本番（live）、ペーパートレード（paper_trading）、開発（development）で動作を切り替えられる設計になっています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - ExecutionEngine の起動
  - Monitoring の起動
  - Paper Trading 検証レポート
  - AI（ニュース NLP / レジーム判定）の利用
- 実行フロー / ファイルフラグ
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システム「KabuSys」の実装。
- データ格納に DuckDB（分析用）と SQLite（監視・注文ログ）を使用。
- 発注系は kabuステーション API を呼ぶ実装（paper_trading では MockBrokerClient を利用して DB を分離）。
- 監視コンポーネントはシステム稼働/データ鮮度/滞留注文/リスク（ドローダウン・ポジション数）をチェックし、必要に応じて kill.flag を書き込む等の運用ガードを提供。
- 研究（research）モジュールはファクター計算・特徴量探索機能を提供。
- AI モジュールは OpenAI API を用いたニュースセンチメント / 市場レジーム判定を行う。

---

主な機能一覧
- execution/
  - ExecutionEngine: 発注の実行・管理（ブローカ抽象化、リスク管理、オーダー管理、リコンシリエーション）
  - paper_trading モードで本番 DB と分離（data/paper_trading.db）
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - kill_switch: 条件に応じて data/kill.flag を作成して ExecutionEngine 停止を誘導
  - MonitoringDB: SQLite に監視ログを永続化
- portfolio/
  - 銘柄選定、重み計算、ポジションサイズ算出、セクター制約・レジーム乗数
- research/
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリ
- ai/
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores テーブルへの書込）
  - regime_detector: マクロ記事 + ETF MA に基づく市場レジーム判定
- utils/
  - logging_setup: 一貫したログ設定（stdout と日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity の設定ユーティリティ
- tools/
  - paper_verification_report: ペーパートレード結果の集約・合否レポート生成
- CLI ツール
  - config_setup: .env の対話式ウィザード
  - validate_config: .env / config/*.yaml の起動前チェック

---

セットアップ手順（ローカル開発向け）
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化（venv / poetry 等）

2. 依存パッケージをインストール
   - 必要なパッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証時）
   - 例: pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml があるディレクトリ）
   - Settings は自動でプロジェクトルートを検出し、.env / .env.local を読み込みます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を環境変数に設定（または .env に追加）
   - 重要: .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ
   - デフォルトで以下のファイルを使います（.env で上書き可能）
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (監視 SQLite)
     - data/paper_trading.db (paper_trading 用 SQLite)
   - ログディレクトリ: logs/（LOG_DIR 環境変数で変更可能）

---

使い方（主要コマンド）
- 環境作成（.env）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番/開発/ペーパーは KABUSYS_ENV 環境変数で切替
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了する
    - 実行中に stop フラグ（data/stop_requested.flag）をファイル作成するとエンジンを停止
    - 実行時にプロセス優先度を "high" に設定し、PID は data/execution.pid に管理されます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト: 60）
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使用（KABUSYS_ENV に依存しない）
  - 停止: data/stop_requested.flag を作成すると監視ループが終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスはオプション --db または 環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- AI 機能（プログラムから）
  - OpenAI API キーをセットして呼び出し
  - 例（Python REPL / スクリプト）:
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,20), api_key="sk-...")

  - regime_detector も同様に:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,20), api_key="...")

  - 注意: OPENAI_API_KEY が未設定だと ValueError になります。モデルは gpt-4o-mini を利用する設計。

---

主要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
- ストレージ
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- ロギング / 実行
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (logs の代替ディレクトリ)
  - PID_FILE_PATH (ExecutionEngine 用の pid ファイル)
- その他
  - OPENAI_API_KEY (AI 機能用)
  - PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒, default=60)
  - KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag を自動クリア。production では 0 推奨)

---

実行フロー / 停止・ガード機構
- stop フラグ:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のメインループが検知して終了します。
- kill.flag（Kill Switch）:
  - Monitoring の条件（ドローダウン超過 / ポジション上限など）により data/kill.flag が作成されると ExecutionEngine に停止シグナルを送る運用になります。
  - Settings.kill_flag_clear_on_start が 1 の場合、Execution 起動時に自動で kill.flag をクリアします（本番では危険）。
- DB 書き込み:
  - monitoring は init_monitoring_db で必要なテーブルを冪等に作成します。既存 DB に対するマイグレーション（カラム追加）処理も含む設計です。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
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
    - alert_manager.py (参照されるが本リストにない場合あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

プロジェクトルート（参照）
- .env, .env.local  — 環境変数ファイル（.env は生成・管理に注意）
- config/*.yaml — 設定テンプレート（generate スクリプトあり）
- data/ — データファイル（SQLite / kill.flag / stop_requested.flag / pid 等）
- logs/ — ログファイル（app_name.log を日次ローテート）

---

開発者向けメモ / 注意点
- .env は絶対に Git にコミットしないでください。
- Monitoring は sqlite_path （監視 DB）に常に接続します。Execution は KABUSYS_ENV により paper_trading 用 DB を使い分けます（本番 DB とペーパーを完全分離）。
- OpenAI 連携は API のレートやエラーに対してリトライ戦略が実装されていますが、APIキー/コストに注意してください。
- logging_setup は stdout とファイル両方に出力します。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで動作します。
- process_priority により起動時にプロセス優先度を上げますが、権限不足で設定できない場合は警告でスキップされます。

---

サポート / 追記
- 本 README はコードベースの現状を簡潔にまとめたものです。細かなパラメータや内部挙動は各モジュールのドキュメンテーション（モジュール内 docstring）を参照してください。
- 追加の実行方法やデプロイ手順（systemd / コンテナ化 / CI 設定等）が必要であれば別途ドキュメント化します。