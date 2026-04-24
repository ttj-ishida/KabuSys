# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Unreleased: 現在開発中の変更点（空欄または作業中のメモ）
- リリースごとに日時付きで機能追加・変更・修正等を記載

## [Unreleased]
- なし

## [0.1.0] - 2026-04-24

Added
- 全体
  - 初期バージョンを追加（__version__ = "0.1.0"）。
  - Python パッケージとしての基本構成を追加（execution, monitoring, portfolio, utils, research, tools 等のモジュール群）。

- 設定管理
  - Settings クラスを導入して環境変数/設定値を一元管理。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサを改善: export 形式、引用符付き値、インラインコメントの扱い等に対応。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - PAPER_FILL_MODE（ペーパートレードの約定モデル）に対する検証を追加（有効値: "instant", "partial", "never", "reject"）。
  - 各種パスや閾値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK 閾値 など）を Settings から取得可能に。

- 設定ツール / 検証
  - 環境設定ウィザード (kabusys.config_setup) を追加。対話式で .env を初期作成/更新可能。
    - デフォルト値、シークレット扱い、選択肢提示、保存の確認を実装。
    - .env 書き込み時にテンプレートヘッダを付加。
  - 設定検証 CLI (kabusys.validate_config) を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML があれば）を検証。
    - --strict オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト (kabusys.run_execution) を追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用）。
    - BrokerClientFactory を使ってブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler 等を組み立てて ExecutionEngine を起動。
    - プロセス優先度を高に設定して起動（utils.process_priority 経由）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。実行 PID を data/execution.pid に出力。
    - RiskManager デフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内で定義。
  - 監視ループ起動スクリプト (kabusys.run_monitoring) を追加。
    - SystemMonitor を初期化してポーリングループを実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックして警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 監視 / 検査ツール
  - Paper Trading 検証レポート生成スクリプト (kabusys.tools.paper_verification_report) を追加。
    - SQLite の paper_trading DB を読み、system_status / trade_logs / risk_logs から指標を集計してレポート出力。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、レイテンシ（avg/max/P95）等。
    - Pass/Fail 判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - --from/--to/--db オプションで期間・DB を指定可能。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み計算モジュール (kabusys.portfolio.portfolio_builder) を追加。
    - select_candidates: スコア降順で上位 N を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分 / スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数 (kabusys.portfolio.risk_adjustment) を追加。
    - apply_sector_cap: 既存保有のセクターエクスポージャが閾値を超える場合、新規候補を除外するロジック。
      - unknown セクターは上限適用対象外。
      - 当日売却予定の銘柄をエクスポージャ計算から除外するオプションをサポート。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 でフォールバック）。
  - 株数決定・リスク制限 (kabusys.portfolio.position_sizing) を追加。
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて発注株数を計算。
    - lot_size（単元株）や cost_buffer（手数料/スリッページ想定）を考慮した aggregate cap（全体投下上限）とスケーリングロジックを実装。
    - risk_based では risk_pct / stop_loss_pct を用いたポジションサイズ算出を実装。
    - 価格欠損時のスキップや各種上限・丸め処理を考慮。

- ユーティリティ
  - ロギング設定ユーティリティ (kabusys.utils.logging_setup) を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリの自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。
    - ログレベル/ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority) を追加。
    - Windows / POSIX の差分を吸収して nice 値や Windows の priority クラスを設定。
    - set_process_priority(level) で "high" / "normal" / "low" を指定可能。アクセス拒否等は警告でスキップ。
    - set_cpu_affinity(cpu_count) によるコア固定機能を実装（未指定はスキップ）。

- リサーチ（factor）
  - ファクター計算モジュール (kabusys.research.factor_research) を追加。
    - Momentum, Value, Volatility, Liquidity 等のファクター算出方針と定数を記載。
    - calc_momentum の実装着手（モメンタム指標: 1M/3M/6M 返還、MA200 乖離率等）。注: ファイル末尾で calc_momentum 実装の続きが未完了の箇所あり（WIP）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / Known issues
- factor_research.calc_momentum の実装がファイル末尾で途切れており、未完の状態（実装継続が必要）。
- 一部 TODO コメントあり（例: position_sizing の銘柄ごとの lot_size 対応、risk_adjustment の price フォールバック等）。
- 実際のブローカークライアント実装 (BrokerClientFactory / MockBrokerClient / ExecutionEngine の内部等) は本 changelog のコード一覧に依存するが、ここではインターフェースと起動フローのみ記載。

Acknowledgements
- 本リリースはシステム設計書（PortfolioConstruction.md, StrategyModel.md 等）に基づく実装方針を反映しています。