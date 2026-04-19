# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョニングはパッケージの `__version__`（現行: 0.1.0）に基づきます。

注: 以下の変更点はリポジトリ内のソースコードから推測して記載した要約です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

Added
- 初期リリース: KabuSys (日本株自動売買システム) のコア機能を追加。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて paper_trading 用の分離された SQLite（data/paper_trading.db）と MockBrokerClient を利用可能。プロセス優先度設定、PID ファイル管理、停止フラグ検出、デーモンスレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可。監視用 DB は環境に関わらず本番 sqlite_path を使用（監視テーブル初期化を行う）。
- 設定管理:
  - config.py: Settings クラスを追加。`.env` / `.env.local` の自動ロード（プロジェクトルート検出 .git または pyproject.toml）、環境変数のパース（export 形式、クォート値、インラインコメント処理）を実装。多くの設定プロパティ（J-Quants、kabuAPI、LINE、DB パス、paper_trading 用パス、監視閾値、環境判定フラグ等）を提供。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。既存値の再利用、シークレットマスク、入力確認、ファイル書き込みを実装。
  - validate_config.py: 起動前チェック CLI。必須環境変数や KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ:
  - utils/logging_setup.py: setup_logging を実装。コンソールは stdout に出力し、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。LOG_DIR / LOG_LEVEL の解決順、ハンドラの二重設定防止、ディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: set_process_priority と set_cpu_affinity を実装。Windows (psutil の優先度クラス) と POSIX (nice 値) を吸収し、権限不足などの失敗時は警告を出してスキップする。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知値は 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に基づいて発注株数を算出。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケーリング（cost_buffer 考慮）、available_cash に応じたスケールダウンと残差処理を実装。
- リサーチ / ファクター:
  - research/factor_research.py（部分実装を含む）: モメンタム等のファクター計算を行う設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を明記。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、閾値に基づく PASS/FAIL 判定を行う。コマンドラインで期間指定・DB パス指定が可能。
- DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。run_execution/run_monitoring の両方で初期化（環境に応じ DB パスは分離）。
- 実行 / 安全機構:
  - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid 等）で外部停止制御を行う仕組みを導入。KILL フラグの自動クリア設定もサポート（KILL_FLAG_CLEAR_ON_START）。
- ドキュメント的コメント:
  - 多数のモジュールに設計方針・使用法・注意事項を docstring とコメントで追加（例: PortfolioConstruction.md、StrategyModel.md への参照や TODO 注記）。

Changed
- 初回リリースのため該当なし（新規追加中心）。

Fixed
- 設定読み込み周りの堅牢化:
  - .env パーサの改善（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理、空行/コメント行の無視）により様々な .env フォーマットに耐性を持たせた。
- ロギング・ファイル処理のフォールバック強化:
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時にコンソール出力にフォールバックする実装で障害時の情報喪失を低減。

Security
- .env ファイルに関する注意喚起を config_setup.py のヘッダコメントで明記（絶対に Git にコミットしないこと）。

Notes / Migration
- .env 自動読み込み:
  - デフォルトでプロジェクトルートの .env/.env.local を自動ロードします。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live の DB 分離:
  - paper_trading モードでは paper 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離されます。
- Kill Switch / Flag の扱い:
  - 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 のまま運用することを推奨します（自動クリアは危険）。
- ログ:
  - デフォルトは logs/<app_name>.log を日次ローテーションで保存（30 日保持）。ログディレクトリの権限・存在確認を事前に行ってください。

References
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"
- 実行例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report

--- 

（以上）