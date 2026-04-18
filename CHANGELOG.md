# Changelog

すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。    

現在のパッケージバージョン: 0.1.0

---

## [0.1.0] - 2026-04-18

### Added
- 初期リリースを追加。
- 実行・監視用エントリポイントを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV に応じて Paper Trading 用の専用 SQLite（data/paper_trading.db）を使い、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモン実行と停止フラグ（data/stop_requested.flag）監視を実装。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了。
- 設定管理とウィザード:
  - config.py
    - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなど）。
    - Settings クラスで各種設定値をプロパティとして提供（J-Quants, kabu API, DuckDB/SQLite パス, PAPER_FILL_MODE, PID/KILL フラグ設定, CPU/MEM/DISK 閾値, 環境判定ユーティリティ等）。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。シークレット項目のマスク表示、既存 .env の読み込み、最終確認・保存機能を提供。
- 設定検証 CLI:
  - validate_config.py
    - .env と config/*.yaml の基本的な設定検証を行う CLI。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在する場合）の検証、本番環境に対する追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギングユーティリティ:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ログディレクトリ作成の失敗時はファイル出力をスキップしてコンソールログのみで継続。
    - ログレベル解決順序およびログディレクトリ解決順序を実装。
    - 日次ログの 30 世代保持（backupCount=30）。
- プロセス優先度ユーティリティ:
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定。
    - psutil に基づく実装で、権限エラー等は警告を出してスキップ。
    - set_cpu_affinity を提供（最初の N コアに固定）。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中度上限チェック (apply_sector_cap)、市場レジームに応じた資金乗数 (calc_regime_multiplier) を実装。レジームマップ: bull=1.0, neutral=0.7, bear=0.3。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 発注株数計算 (calc_position_sizes) を実装。allocation_method による分岐（risk_based / equal / score）、lot_size による丸め、per-stock 上限と aggregate cap（利用可能現金）によるスケーリングと端数配分ロジックを実装。cost_buffer により保守的見積りを行う。
- リサーチ / ファクター計算:
  - research/factor_research.py（設計・一部実装）
    - Momentum, Value, Volatility, Liquidity などのファクター群の計算設計を実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - モメンタム周り（関数群の枠組み、定数定義等）を実装。
- ペーパートレード検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH / --db）から統計を集計し検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - 合否基準（デフォルト閾値）を定義: 稼働率 >= 99.0%, 成功率 >= 90.0%, 送信率 >= 95.0%, P95 <= 200ms。
    - P95 計算、データ無しケースのハンドリング、出力フォーマットを実装。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Security
- (該当なし)

### Notes / 実装上の重要な挙動
- .env の自動読み込みはプロジェクトルートが検出された場合にのみ行われ、OS 環境変数は上書きされないよう保護（.env.local は既存 OS 環境変数を保護しつつ上書き可能）。
- config.Settngs のプロパティは起動時の環境変数を即座に参照するため、テストやスクリプト内で環境変数を変更する場合は注意が必要。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックすることで監視ループのクラッシュを防止する設計。
- run_execution は起動前に停止フラグが立っている場合は起動を中止する安全処理を備える。
- logging_setup はログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、標準出力のみで動作継続するフォールバックを実装。
- process_priority / cpu_affinity の設定は実行環境の権限や OS に依存するため、失敗時は警告が出て安全に続行する。

### Migration / Upgrade notes
- なし（初回公開）。既存の運用を開始する際は以下を確認してください:
  - .env を作成し、必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）を設定する。
  - KABUSYS_ENV を適切に設定（development / paper_trading / live）。
  - Paper Trading を使用する場合は PAPER_TRADING_SQLITE_PATH を設定するかデフォルトの data/paper_trading.db を利用する。
  - ログ出力先を変更したい場合は LOG_DIR 環境変数を設定する。
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0（デフォルト）にすることを推奨。

---

今後のリリースでは、StrategyModel や ExecutionEngine の詳細実装、テストカバレッジの追加、errors/metrics の拡充、YAML ベースの詳細設定読み込みなどを予定しています。ご要望や不具合は issue を作成してください。