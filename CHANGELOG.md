# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

初期リリース — 基本機能一式を実装しました。

### Added
- 全体
  - パッケージ初期公開。バージョンは `__version__ = "0.1.0"`。
  - 基本的なログ出力は INFO レベルで初期化するエントリポイントを提供。

- 設定関連
  - Settings クラス（kabusys.config）を実装し、環境変数から各種設定を取得。
    - DB パス、LINE トークン、kabuAPI 設定、Paper Trading 用の各種設定などをプロパティ経由で取得。
    - env 値（development / paper_trading / live）、LOG_LEVEL の検証を実装。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - 自動 .env ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索し、.env / .env.local を読み込む。
    - OS 環境変数は保護（上書き回避）する仕組みを採用。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能。
    - .env のパースは `export KEY=val`、クォート、インラインコメントなどに対応。
  - 対話式設定ウィザード（kabusys.config_setup）を追加。
    - .env の初期作成・更新を支援。主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を用意。
    - 保存時の注意喚起（.env を Git にコミットしないこと）を出力。

- 設定検証
  - CLI 検証ツール（kabusys.validate_config）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML が無ければスキップ）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行および監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。MockBrokerClient の利用フックを用意（BrokerClientFactory）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ検知および PID ファイルを扱う。
    - RiskManager に渡すデフォルト構成値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を定義し、初期 portfolio value は broker.get_available_cash() を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はログを出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計で、init_monitoring_db によるテーブル初期化を行う。
    - 停止フラグファイルを監視し、安全にループを終了する仕組みを実装。

- データベース / 分析
  - DuckDB と SQLite の両方を利用する設計。
    - デフォルトパス: DuckDB `data/kabusys.duckdb`, SQLite `data/monitoring.db`、Paper Trading 用 `data/paper_trading.db`。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分（スコア合計が0の場合は等分配にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限（max_sector_pct）超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（未定義は警告の上 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
    - 単元株（lot_size）での丸め処理、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、コストバッファ（cost_buffer）を考慮した aggregate cap のスケーリング、残差に基づく追加配分ロジックを実装。

- リサーチ / ファクター
  - research.factor_research:
    - calc_momentum: mom_1m/3m/6m と MA200 乖離率を DuckDB の SQL ウィンドウ関数で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（true_range の NULL 伝播制御を含む）。
    - 計算に必要なスキャン幅やウィンドウ長は定数化されている（例: MA200=200, ATR_DAYS=20 など）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成 CLI を実装。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し、閾値比較で PASS/FAIL を判定（閾値はソース内定義）。
    - 日付レンジ指定（--from / --to）と DB パス指定（--db）に対応。

- ユーティリティ
  - utils.process_priority:
    - プラットフォーム差を吸収する set_process_priority(level) を実装（Windows と POSIX(Linux/Mac/FreeBSD) に対応）。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は変更しない）。どちらも権限不足や未サポート環境では警告を出して安全にスキップ。

### Changed
- （このリリースは初回公開のため該当なし）

### Fixed
- （このリリースは初回公開のため該当なし）

### Security
- .env の取り扱いに関する注意喚起を config_setup に記載（.env をリポジトリにコミットしないこと）。
- 自動 .env 読み込み時に OS の環境変数は保護する実装（上書き回避）。

---

注意:
- 各 CLI / スクリプトは標準ライブラリ以外に psutil / duckdb / PyYAML（任意）等の依存があるため、実行環境で必要なパッケージを準備してください。
- 本番運用時は KABUSYS_ENV の設定や KILL/STOP フラグの取り扱いに十分ご注意ください（validate_config の live 向けチェックを参照）。