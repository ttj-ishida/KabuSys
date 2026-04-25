CHANGELOG
=========

すべての注目すべき変更履歴を記載します。フォーマットは "Keep a Changelog" に準拠しています。

記載方針:
- 変更はコードベースから推測してまとめています。
- 初期リリース (v0.1.0) として主要な追加機能・ユーティリティを列挙しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

Added
- 初回公開: KabuSys パッケージを v0.1.0 として追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite / DuckDB 接続、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでの engine.run_session 実行、data/stop_requested.flag による安全停止、paper_trading 環境時は専用 DB（data/paper_trading.db）を使用する仕組みを含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。停止フラグで安全終了。
- 環境設定・検証 CLI
  - config_setup.py: .env の対話式生成・更新ウィザードを追加（.env の初期作成や既存値の再利用に対応）。
  - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。--strict オプションで警告を FAIL 扱いにできる。
- 環境設定管理
  - config.py: Settings クラスを追加。環境変数の自動ロード（プロジェクトルートの .env と .env.local を読み込み、.env.local は上書き）および各種プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）とバリデーションを提供。.env の柔軟なパース（export プレフィックス、クォート、インラインコメントの扱い）や OS 環境変数保護を実装。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度設定（set_process_priority）と CPU Affinity 設定（set_cpu_affinity）を追加。Windows / POSIX の差を吸収して安全に呼び出せる実装（psutil ベース）。失敗時は警告でフォールバック。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 銘柄候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア合計が 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく資金乗数 calc_regime_multiplier（未知レジームは警告して 1.0 にフォールバック）を実装。
  - portfolio/position_sizing.py: 発注株数算出アルゴリズムを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）で丸め、ポートフォリオ上限や個別上限を考慮した aggregate スケーリング（余りの分配ロジックを含む）を実装。コストバッファ（手数料・スリッページ想定）対応。
- 分析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定。--from / --to / --db オプションおよび PAPER_TRADING_SQLITE_PATH 環境変数に対応。デフォルト閾値を定義（稼働率 99% など）。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、MA200 乖離、ATR、流動性等の計算）を追加（設計方針、定数、関数定義を含む）。

Changed
- 初回リリースのため、コードベースの主要設計方針・ API を文書化（docstring を含む）。ロギング / DB パス等のデフォルト値を一貫化（data/ 配下、logs/ 等）。

Fixed / Robustness improvements
- MONITOR_POLL_INTERVAL の不正値（0 や非整数）に対してフォールバックと警告を追加（time.sleep に渡す不正値を防止）。
- logging_setup: 既存ハンドラを一度 flush/close 後に削除して二重登録を防止。ログディレクトリ作成失敗時もコンソールログにフォールバック。
- process_priority / set_cpu_affinity: サポート外 OS やアクセス権限不足時に例外で落ちないよう警告でスキップ。
- calc_score_weights: 全スコア 0 の場合に等金額配分へ自動フォールバックすることでゼロ除算や不正な重みを防止。
- apply_sector_cap: "unknown" セクター（マップに未登録の銘柄）をセクター上限適用外とし、誤って除外されることを回避。
- calc_position_sizes: 価格欠損時のスキップ、単元丸め、aggregate スケーリング時の再配分ロジックにより過大発注を防止。

Notes / 運用上の重要点（ユーザ向け）
- 環境変数自動ロード:
  - 自動ロードはデフォルトで有効。プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、.env を読み込み、.env.local を上書き読み込みします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトの DB / ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite (デフォルト): data/paper_trading.db（KABUSYS_ENV=paper_trading 使用時はこれを優先）
  - ログディレクトリ: logs/（ログファイルは <app_name>.log）
- 停止制御:
  - 停止フラグ: data/stop_requested.flag を作成することで run_monitoring/run_execution を安全に停止できます。
  - 実行中のエンジン用 PID ファイルは data/execution.pid（デフォルト）など。
- 本番ガード:
  - validate_config は KABUSYS_ENV=live の場合に追加警告（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険性等）を出します。--strict を使うと警告も失敗扱いになります。

References
- この CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）を解析して作成しています。実装の詳細については各モジュールの docstring / ソースコードを参照してください。