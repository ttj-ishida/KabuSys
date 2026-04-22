# KabuSys

日本株向け自動売買システムの一部をまとめた Python パッケージです。本リポジトリは取引実行・監視・リサーチ・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）などのモジュール群を含みます。

以下はこのコードベースの README（日本語）です。

注意: 本 README はソースコードを参照して作成しています。実行前に必ず .env を作成し、設定検証を行ってください。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（.env）と主な設定項目
- 使い方（起動・ユーティリティ）
- 停止・Kill Switch の扱い
- ディレクトリ構成（主要ファイル説明）
- 開発者向けメモ

---

プロジェクト概要
- KabuSys は日本株の自動売買に関わるコンポーネント群を提供します。
- 取引実行（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB を使ったファクター計算・特徴量解析）、ポートフォリオ構築、ニュース NLP（OpenAI を利用したセンチメントスコアリング）、レジーム判定などの機能を含みます。
- 設定は主に環境変数（.env）で管理され、.env 作成ウィザード・検証ツールが用意されています。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（モックブローカー）/ live の切替
  - paper_trading の場合は paper_trading.db にデータを分離保存
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視
- Monitoring（run_monitoring.py / monitoring package）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねたポーリング監視
  - kill.flag を書くことで ExecutionEngine に安全停止を指示する KillSwitch
  - 監視データは SQLite（デフォルト data/monitoring.db）へ格納
- Research（duckdb ベース）
  - ファクター計算（Momentum, Volatility, Value など）
  - 将来リターン計算、IC（情報係数）、統計サマリーなど
- Portfolio モジュール
  - 候補選定、等分・スコア加重配分、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF（1321）の MA200 とマクロニュース（LLM）を合成して market_regime を算出・永続化
- ツール
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL 判定レポートを出力
- ユーティリティ
  - config_setup.py: .env の対話式ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - logging_setup, process_priority ユーティリティ

前提条件
- Python 3.9+（型注釈により 3.9 以降を想定）
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML の構文検査を行う場合に推奨）
- SQLite（Python 標準ライブラリに同梱）
- （任意）OpenAI API キー（ニューススコアやレジーム判定を利用する場合）

セットアップ手順（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他の依存を追加してください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（下記「環境変数」を参照）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - エラーがあると exit(1) を返します。--strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリ
   - デフォルトで data/ と logs/ を利用します。必要なら .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。

環境変数（.env）と主な設定項目
- 必須（少なくともテスト時に必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 環境
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
    - paper_trading: 発注はモック。paper_trading 用 DB に記録
- DB 関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- OpenAI
  - OPENAI_API_KEY: ニュース NLP / レジーム判定で使用
- ロギング
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (省略時 logs/)
- LINE（通知）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）
- Kill / PID
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1): ExecutionEngine 起動時に kill.flag を自動でクリアするか
- 監視
  - CPU/MEM/DISK 閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

使い方（代表的なコマンド）
- .env の作成・更新（対話）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（実行ユーザにより権限不足で警告になることがあります）。
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録します。
    - data/execution.pid に PID を書きます。
    - data/stop_requested.flag があれば起動せず終了します。外部から停止するには stop フラグ（下記参照）を使用します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - Monitoring は常に本番設定の sqlite_path を参照して監視ログを書きます（環境にかかわらず同一の監視 DB を使用）。

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH による指定も可能

- AI / リサーチ機能（プログラム的呼び出し）
  - ニューススコア付与: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - リサーチ: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等
  - これらは直接モジュール API を利用する想定（CLI ではなく Python 呼び出し）

停止・Kill Switch の扱い
- ExecutionEngine の停止は主に以下の方法で行います:
  - data/stop_requested.flag: run_execution.py / run_monitoring.py はこのファイルをチェックし、存在すれば安全にシャットダウンします（外部プロセスからの `touch data/stop_requested.flag` 相当）。
  - Kill Switch: 監視モジュール（KillSwitch）はリスクイベント（ドローダウン超過等）を検出した場合に data/kill.flag に理由を書き込みます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を参照して自動クリアするかを決めます。
  - 強制終了: 直接プロセスを kill する方法もありますが、データ整合性の観点からまずは上記フラグによる停止を推奨します。

ログ
- ログは logs/<app_name>.log に日次ローテート（30日保持）で出力されます。コンソールは stdout に出力されます。
- setup_logging(app_name="execution" / "monitoring") を起動スクリプトが呼んで統一的な設定を行います。
- LOG_DIR 環境変数で変更可能。

ディレクトリ構成（主要ファイル・説明）
- src/kabusys/
  - __init__.py
    - パッケージ定義・バージョン
  - config.py
    - 環境変数読み込み・.env 自動ロード・Settings クラス（アプリ設定）
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の切替、PID/stop フラグ管理）
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - monitoring/
    - monitoring_db.py: SQLite スキーマ作成・MonitoringDB クラス（読み書き）
    - system_monitor.py: システム状態・データ鮮度チェック
    - trade_monitor.py: 発注ログ監視（存在するがここでの説明省略）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag 制御
    - monitoring_engine.py: 各 Monitor を束ねるランナー
    - alert_manager.py: 通知（LINE 等）を扱う（存在）
  - execution/
    - execution_engine.py, order_manager.py, risk_manager.py, reconciler.py, broker_factory.py, order_repository.py
      - Execution の中核、ブローカー抽象化、リスク管理、注文管理、データ永続化など
  - portfolio/
    - portfolio_builder.py: 候補選定・重み算出
    - position_sizing.py: 株数決定・スケールダウン処理
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum/value/volatility）
    - feature_exploration.py: 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI 経由）
    - regime_detector.py: レジーム判定（MA200 + マクロニュース）
  - data/ (実行時に生成・使用する想定)
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（DUCKDB_PATH）
    - execution.pid / stop_requested.flag / kill.flag などのフラグ・PID ファイル
  - tools/
    - paper_verification_report.py: ペーパートレードの検証レポート出力ツール

開発者向けメモ / 注意点
- auto .env ロードは config.py がプロジェクトルートを .git または pyproject.toml から探索して行います。テスト時や特殊用途で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の DB 初期化（init_monitoring_db）は冪等に実装されています。既存 DB にカラムを追加する簡易マイグレーションロジックが含まれます（例: trade_logs に latency_ms を追加）。
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・フォールバックの実装があり、API 失敗時はフェイルセーフ（例: マクロセンチメント失敗 → 0.0 フォールバック）します。ただし API キー未設定時は例外を投げます。
- process_priority 設定は psutil を使います。権限がないと設定に失敗することがあるのでログで確認してください。
- DuckDB を使った研究機能は prices_daily / raw_financials / raw_news 等のテーブルが前提です。データ投入は別スクリプト等で行ってください。

サンプル .env（最低限）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=（必要時）
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

最後に
- 実行前に python -m kabusys.config_setup → python -m kabusys.validate_config の順で設定を整えることを推奨します。
- 本リポジトリは取引ロジック・資金管理に関わるため、本番環境（KABUSYS_ENV=live）での運用は十分なテスト・監査を行い、LINE 通知等のアラート設定を確認してから行ってください。

必要があれば、この README を README.md として出力する形でファイル化するほか、起動手順のサンプルスクリプトや systemd ユニット定義、Dockerfile などの追加も支援できます。どの形式がよいか指示してください。