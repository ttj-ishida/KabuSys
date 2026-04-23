# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティック バージョニングを採用します。

## [0.1.0] - 2026-04-23

### Added
- 初期公開リリース。以下の主要機能・モジュールを追加。
  - 実行エントリスクリプト
    - run_execution.py
      - ExecutionEngine を起動するスクリプト。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離して動作。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止用フラグファイル（data/stop_requested.flag）検出による安全な停止処理。
      - 実行 pid を data/execution.pid に保管する仕組みをサポート。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
      - Monitoring は環境に関わらず本番用 sqlite_path を使用する（監視用 DB の初期化処理を実行）。
      - DuckDB への接続を確立し、監視処理で利用。
      - 停止フラグ検出でループ終了、KeyboardInterrupt ハンドリング、例外時のログ出力。

  - 設定管理
    - config.py
      - 環境変数および .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
      - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 複数の設定プロパティを提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値、環境判定等）。
      - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、PID ファイル等のデフォルト値。
      - Settings クラスと単一インスタンス settings を公開。
      - .env パースロジックは引用符や export プレフィックス、インラインコメントの扱いに対応。
    - config_setup.py
      - 対話式 .env ウィザード（初期作成・更新用）。
      - 各種項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等）を対話的にセットし .env を生成。
      - 既存 .env 読み込み、シークレットはマスク表示、保存確認を経て file 出力。
    - validate_config.py
      - 起動前設定検証 CLI。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill Switch のクリア設定に関する警告）。
      - --strict オプションで警告を failure 扱いにできる。

  - ユーティリティ
    - utils/logging_setup.py
      - 統一ログ設定ユーティリティ。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルトログディレクトリ: logs/、30 日保持）をルートロガーに設定。
      - ログレベル・ログディレクトリの解決順序とハンドラ再初期化機能。
      - ファイルハンドラ作成失敗時はコンソール出力のみで継続。
    - utils/process_priority.py
      - プロセス優先度設定 API（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。
      - Windows と POSIX 系の差分を吸収（psutil を利用）。権限不足や未実装場面では警告を出してスキップ。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: シグナルのスコア順ソートと上位選択。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限（既存保有を考慮して新規候補を除外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、最大ポジション比率、利用率上限、コストバッファ、aggregate cap（利用可能現金超過時のスケーリングと端数再分配）等を実装。

  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプト（SQLite DB を参照して稼働率・注文成功率・送信率・レイテンシ等を算出）。
      - デフォルト DB: data/paper_trading.db、PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
      - P95 計算、閾値（稼働率、成立率、送信率、P95 レイテンシ）に基づく PASS/FAIL 判定と詳細出力。
      - コマンドライン引数 --from / --to / --db をサポート。
  - リサーチ
    - research/factor_research.py（実装開始）
      - DuckDB を用いたファクター計算モジュールの骨子（モメンタム、移動平均、ATR、流動性等を想定）。以降の実装で prices_daily / raw_financials を参照して計算する設計。

  - パッケージ化
    - パッケージ初期化 (kabusys.__init__.py) にバージョン __version__ = "0.1.0" を設定。
    - portfolio パッケージで関数群をエクスポートする便利な __all__ を提供。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Security
- N/A（初回リリース）

注記:
- 設定やファイルパスのデフォルトは安全性・運用性を考慮した値が設定されていますが、本番運用前には必ず validate_config.py でチェックし、.env を適切に設定してください。
- .env ファイルは絶対にバージョン管理に含めないでください（config_setup.py のヘッダにも同様の注意書きあり）。

