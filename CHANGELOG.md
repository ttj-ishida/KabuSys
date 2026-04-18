# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
稼働環境に影響する設定や .env の扱いに注意して運用してください。

なお、本ログは配布されているソースコードから推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-18

初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### Added
- パッケージの基本情報
  - バージョンを `__version__ = "0.1.0"` として公開。

- 環境設定 / 設定管理
  - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env パーサー（export 形式、引用符付き値、インラインコメントの取り扱いに対応）。
  - 環境変数の安全な上書き制御（OS 環境変数は protected として扱う）。
  - 環境変数読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを導入し、以下のプロパティを提供（必要に応じてデフォルト値を使用／バリデーションを行う）:
    - J-Quants / kabu API / LINE トークン関連
    - データベースパス: `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`
    - Paper Trading 固有設定: `PAPER_FILL_MODE`
    - 監視・PID・Kill Flag 関連: `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`
    - 監視しきい値: `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`
    - 実行環境フラグ: `KABUSYS_ENV`（development/paper_trading/live）
    - ログレベル: `LOG_LEVEL`

- CLI ツール
  - config_setup (`python -m kabusys.config_setup`)
    - 対話式ウィザードで .env を作成・更新する機能。
    - シークレット入力対応、既存値の再利用、最終確認とファイル出力。
    - .env のテンプレート（重要キー、説明、注記）を生成。
  - validate_config (`python -m kabusys.validate_config`)
    - 起動前に .env と config/*.yaml の基本チェックを行うCLI。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML のパース確認（PyYAML がある場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。

- 実行 / 監視プロセス起動スクリプト
  - run_execution (`src/kabusys/run_execution.py`)
    - プロセス優先度を「high」に設定して起動（utils.process_priority を利用）。
    - 環境に応じて paper_trading 用 DB と本番 DB を分離（`settings.is_paper` 判定）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理（ExecutionEngine は別スレッドで run_session を実行、停止フラグで graceful shutdown）。
    - 実行用 PID ファイル（data/execution.pid）および停止フラグ（data/stop_requested.flag）に対応。
    - RiskManager のデフォルト設定例を組み込み（最大ポジション比率、利用率、レート制限、サーキットブレーカ、最大ドローダウンなど）。
  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満等の不正値はデフォルトにフォールバック）。
    - 起動時にプロセス優先度を「high」に設定。
    - 監視 DB 初期化（監視は環境に関わらず本番 sqlite_path を使用）。
    - DuckDB 接続を併用、SystemMonitor.check_once を定期実行。
    - 停止フラグファイル検出によるループ終了、KeyboardInterrupt にも対応。

- ロギング / プロセス管理ユーティリティ
  - logging_setup
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - ログディレクトリ（LOG_DIR 環境変数）解決と自動作成。失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルは引数 > 環境変数 > デフォルト の順に解決。
  - process_priority
    - Windows / POSIX（Linux / macOS / FreeBSD）向けにプロセス優先度を設定する set_process_priority。
    - psutil ベースで AccessDenied 等に寛容にフォールバックする設計。
    - set_cpu_affinity を提供し、最初の N コアへの固定をサポート（実行環境に依存）。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio_builder
    - select_candidates: score 降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等配分及びスコア正規化配分（スコア合計 0 の場合は等配分でフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限の適用（既存保有のセクター時価を計算し上限超過セクターから新規候補を除外。unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジームに対する投下資金乗数（bull:1.0, neutral:0.7, bear:0.3。未知は 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出。
    - 単元株（lot_size）での丸め、per-position と aggregate の上限、cost_buffer による保守的見積り、available_cash を超過した場合のスケーリングロジック（残差を考慮した lot 単位の追加配分）を実装。

- 研究支援
  - research.factor_research（モジュールの骨子）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity ファクターを計算する設計（モメンタム等の定数・関数の定義あり）。

- 運用支援ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算。
    - デフォルト閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）。
    - 日付フィルタ（--from / --to）および --db オプションをサポート。
    - DB・テーブルが存在しない場合でも例外を吸収して Graceful に N/A を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

## 注意事項 / 運用メモ
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup にも注記あり）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを無効にすることを推奨します（validate_config が警告を出します）。
- run_execution は paper_trading と live を DB レベルで分離します。paper_trading 実行時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- run_monitoring は monitoring 用テーブルを本番 sqlite_path 上に作成する仕様になっています（環境に依存せず本番 sqlite_path を使用）。
- process_priority / cpu_affinity の設定は権限や OS 機能に依存します。設定に失敗した場合は警告を出してスキップします。

もし特定ファイルや機能ごとにより詳細な変更履歴（関数の引数変更、パラメタデフォルトの差分など）が必要であれば、該当箇所を指定してください。