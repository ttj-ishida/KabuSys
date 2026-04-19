# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
現在のパッケージバージョン: 0.1.0

※ 以下はソースコードから推測して作成した変更履歴です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本機能群を実装。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視 DB を初期化。
    - 停止はプロジェクト直下の data/stop_requested.flag を検知して安全に終了。
    - duckdb を使った分析用接続も確立。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient（BrokerClientFactory により生成）により本番 DB と完全分離。
    - 実行はデーモンスレッドで行い、停止フラグ（data/stop_requested.flag）で停止。PID ファイルを data/execution.pid に管理。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority の set_process_priority を利用）。
- 設定管理
  - config.Settings: 環境変数をラップする Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルートの検出、.env, .env.local 読み込み）。OS 環境変数は保護され上書きされない。
    - .env の行パーサは export プレフィックス、クォート、エスケープ、インラインコメントなどに対応。
    - 各種プロパティ: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、閾値（CPU/MEM/DISK）などを提供。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実施。
- 設定関連 CLI
  - config_setup: 対話式ウィザードにより .env を初期作成 / 更新する CLI を追加（シークレット項目のマスク表示、デフォルト/選択肢）。
  - validate_config: .env と config/*.yaml（存在する場合）の検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がある場合）。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: 共通ログ設定ユーティリティを実装。
    - stdout（StreamHandler）出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - 既存ハンドラの二重設定防止、ログディレクトリ自動作成（失敗時はファイルログをスキップ）。
    - LOG_LEVEL / LOG_DIR の優先解決をサポート。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX を吸収して優先度を設定。権限がない場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定（実装可能な環境のみ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順で上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャが所定の割合を超える場合に当該セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based","equal","score"）に基づき発注株数を計算。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリング、端数処理の再配分ロジックを実装。
      - price 欠損時のスキップ、portfolio_value / available_cash に基づく調整。
- Execution 周辺コンポーネント（インターフェース）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（ソースから使用されることを前提に起動スクリプトへ統合）。
  - RiskConfig のデフォルト値を run_execution 内で設定し、初期 available_cash を broker.get_available_cash() から取得。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用し、起動時に監視用テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（平均/最大/P95）。
    - P95 の計算、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定（稼働率 >=99%、fill>=90%、send>=95%、P95<=200ms）。
    - DB が存在しない場合のエラーメッセージを出力。
- 研究用モジュール（部分実装）
  - research.factor_research: Momentum 等のファクター計算モジュールを追加（DuckDB 接続を受け取って prices_daily / raw_financials を参照）。（実装途中の関数あり）

Security
- .env ファイルの自動ロードにおいて OS 環境変数は保護（protected）され、.env.local は override=True だが OS 環境変数は上書きしない実装。

Documentation
- 各 CLI とユーティリティに docstring と起動方法、環境変数の説明を追加（README 相当の案内は .env 作成→validate_config 実行を推奨）。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Notes / 既知の制約
- research.factor_research の実装は途中で切れている箇所があり、完全なファクタ計算チェーンは未完成の可能性あり。
- 一部モジュールは外部依存（psutil, duckdb, PyYAML 等）により実行環境が必要。YAML 検証は PyYAML 未インストール時にスキップされる。
- position_sizing 等は現状で銘柄ごとの lot_size 固有値をサポートしておらず、将来的に拡張を想定（TODO コメントあり）。
- run_execution/run_monitoring は停止フラグファイル（data/stop_requested.flag）や PID ファイルを使用するため、運用時は data ディレクトリの管理に注意。

---

参考: 主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
- PAPER_FILL_MODE（paper_trading 時の fill 挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険）

(この CHANGELOG はソースコードの解析に基づく推測で作成しています。実際のリリースノート作成時は変更履歴やコミットログを参照してください。)