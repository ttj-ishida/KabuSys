README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージ群です。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- 注文実行エンジン（ExecutionEngine）と発注周辺のコンポーネント
- 監視（Monitoring）: システム状態・注文状況・リスク監視、Kill Switch によるエンジン停止
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援機能（ニュース NLP / レジーム検出：OpenAI を利用）
- ユーティリティ（ログ設定・プロセス優先度設定）
- 運用用 CLI（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

注: 多くのコンポーネントは外部 API キー（J-Quants / kabuステーション / OpenAI）や SQLite / DuckDB を使用します。実運用では .env を使って環境変数を管理します。

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup による .env の対話的生成
- 設定検証: python -m kabusys.validate_config で必須環境変数や config/*.yaml を事前チェック
- ExecutionEngine 起動: python -m kabusys.run_execution（KABUSYS_ENV により paper_trading / live を切替）
  - paper_trading では MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- Monitoring 起動: python -m kabusys.run_monitoring（定期ポーリングで状態を監視・ログ永続化）
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用する点に注意
- Kill Switch: 監視結果により data/kill.flag を作成して ExecutionEngine を安全に停止
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report で稼働率や約定率などを集計
- ポートフォリオ構築ライブラリ: 候補選定・スコア重み付け・等配分・リスクベースのサイズ決定
- リサーチ機能: DuckDB 上で Momentum / Volatility / Value 等のファクター計算や IC 計算
- AI 機能: OpenAI を用いたニュースセンチメント（ai_scores）とレジーム判定（market_regime）

セットアップ手順
----------------

1. Python（推奨 3.10 以上）を準備する。

2. 依存パッケージをインストールする（最低限の主要パッケージ例）。
   - 必要なライブラリ: duckdb, psutil, openai（AI 機能を使う場合）, PyYAML（config YAML 検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

3. プロジェクトルートに .env を用意する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、設定の妥当性を確認:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. データディレクトリと DB の初期化
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき）
   - 起動スクリプトは起動時に必要なテーブルを作成する（init_monitoring_db が冪等に作成・マイグレーションします）。

使い方（基本コマンド）
--------------------

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup
  - オプション: --env-file PATH

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit(1)。--strict を付けると警告も失敗扱い。

- ExecutionEngine 起動（本番／ペーパーは KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution （KABUSYS_ENV を .env に設定している場合は不要）
  - 停止:
    - 監視または KillSwitch が data/kill.flag を作成すると Engine は停止します。
    - 手動停止する場合は実行中のプロセスに SIGINT（Ctrl+C）を送るか data/stop_requested.flag を作成します（run scripts が参照）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 停止:
    - 実行中は data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

主要な環境変数（抜粋）
--------------------
 - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
 - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
 - KABUSYS_ENV: 実行環境（development / paper_trading / live）
 - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
 - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
 - SQLITE_PATH: SQLite (監視) パス（デフォルト data/monitoring.db）
 - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
 - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
 - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用）
 - PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
 - KILL_FLAG_CLEAR_ON_START: (0/1) 起動時に kill.flag を自動クリア（テスト用。production では 0 推奨）

運用に関する補足
----------------
- ログ: logs/<app_name>.log に日次ローテートで出力されます（logs ディレクトリは自動作成）。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼んで優先度を上げようとしますが、権限により失敗することがあります（ログに警告が出ます）。
- Kill Switch:
  - KillSwitch は監視結果（ドローダウン閾値超過やポジション上限超過）により data/kill.flag を作成します。ExecutionEngine はこのフラグを検出して安全停止します。
  - 手動でクリアする場合: rm data/kill.flag
- 停止フラグ:
  - run_monitoring/run_execution はプロジェクト内の data/stop_requested.flag を監視しています。停止時にこのファイルを作成するとそれぞれ安全に終了します。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリの構成です（リポジトリは src 配下にパッケージを配置する構成を想定）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/Settings 管理、.env 自動読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI を利用して ai_scores を生成）
    - regime_detector.py       — レジーム判定（MA + macro sentiment）
  - monitoring/
    - monitoring_db.py         — SQLite ベースの監視 DB 層
    - system_monitor.py        — システム状態・データ鮮度チェック
    - trade_monitor.py         — （注文監視ロジック）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - monitoring_engine.py     — 複数モニタの統合とアラート/kill 評価
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — （LINE 等への通知ラッパー想定）
  - execution/
    - execution_engine.py      — ExecutionEngine（セッション実行ロジック）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 株数決定・スケールダウンロジック
    - risk_adjustment.py       — セクター制限 / レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - data/                      — 実行時生成されるデータファイル（DB / PID / flag 等）

注意事項 / ベストプラクティス
------------------------------
- .env は絶対にリポジトリにコミットしないでください。.env は機密情報（API キー等）を含みます。
- KABUSYS_ENV=live の場合は特に注意して設定を確認してください（validate_config の live ガードを参照）。
- OpenAI API を使う機能（ニュース NLP / レジーム判定）は API 呼び出しの失敗に対してフェイルセーフ処理がありますが、API キーの管理とコストに注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されるよう設計されています。ペーパートレードの DB を指定して安全に検証してください。

参考コマンド例
--------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動（デフォルト 60 秒ポーリング）:
  - python -m kabusys.run_monitoring
- 監視ポーリング間隔を 30 秒にする:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- ExecutionEngine をペーパートレードモードで起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート (DB を明示指定):
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

問い合わせ / 開発メモ
--------------------
- 新しい設定項目を追加したら config_setup.py と validate_config.py を更新してください。
- DuckDB に依存するリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルに依存します。データの投入方法は別途スクリプト（data pipeline）を参照してください。
- テストでは外部 API 呼び出し（OpenAI やブローカークライアント）をモックしてください。README に書かれている関数群は単体でモック可能な設計になっています。

以上が本コードベースの概要と運用手順です。必要があれば、環境変数の完全な一覧や起動フロー図・例外処理ポリシー等の追加ドキュメントを作成します。