# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

注: コードベースから推測して作成しています。実装上の意図・未実装箇所・TODO 等は "既知の問題 / 注意点" セクションで補足しています。

## [Unreleased]

- 研究用モジュール（kabusys.research）や一部の機能は開発途中です。詳細は既知の問題参照。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期リリース相当の主要モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境
  - 環境変数管理モジュール (kabusys.config) を追加。
    - プロジェクトルートを .git または pyproject.toml から検出し、.env/.env.local を自動読み込み（OS 環境変数を保護）。
    - .env の堅牢なパーサを実装（export プレフィックス対応、クォート文字列・バックスラッシュエスケープ処理、インラインコメント処理）。
    - Settings クラスで各種設定プロパティを提供（J-Quants、kabu API、DuckDB/SQLite パス、Paper Trading 設定、監視閾値、ログレベル等）。
    - PAPER_FILL_MODE の妥当性チェックと PAPER_TRADING_SQLITE_PATH のサポート。
  - 対話式設定ウィザード CLI (kabusys.config_setup) を追加。
    - .env の初期作成・更新を支援。シークレットのマスク表示、デフォルト値・選択肢サポート、保存前の確認を実装。
  - 設定検証 CLI (kabusys.validate_config) を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在／パース検証（PyYAML インストール状況に依存）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト (kabusys.run_execution) を追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper 用専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（本番/モックの切り替えを想定）。
    - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine 等の組立て・起動ロジックを実装。
    - エンジンは別スレッドで実行され、停止フラグ (data/stop_requested.flag) による安全停止をサポート。PID ファイル出力に対応。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期ポートフォリオ値を broker.get_available_cash() から取得。
  - 監視ループ起動スクリプト (kabusys.run_monitoring) を追加。
    - SystemMonitor を初期化し、ポーリングループを実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告）。
    - 監視用 DB は環境にかかわらず production 相当の sqlite_path を使用する（監視データは専用に保持）。
    - 停止フラグ検知でループを終了。KeyboardInterrupt をハンドリングしてクリーンに終了。

- ロギング・プロセス管理
  - ロギングユーティリティ (kabusys.utils.logging_setup) を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順序を明確化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority) を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加:
    - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
    - risk_adjustment: セクター集中制限適用（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方法をサポートし、単元株（lot_size）丸め、aggregate cap によるスケールダウン、コストバッファ考慮、端数配分アルゴリズムを実装。
  - API は純粋関数化されており DB 非依存でメモリ内計算のみ。

- ツール
  - Paper Trading 検証レポート生成スクリプト (kabusys.tools.paper_verification_report) を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算し標準出力でレポート表示。
    - デフォルト DB は data/paper_trading.db、コマンドラインで期間指定・DB パス上書き可。
    - 基準値（稼働率 99%、fill 90%、send 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を実装。

- 研究用
  - kabusys.research.factor_research の骨格を追加。モメンタム系ファクター計算関数の実装を開始（calc_momentum の追加、DuckDB 接続を前提）。

### Changed
- .env 自動ロードの優先順を明確化: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護され上書きされない）。
- ログ出力は標準エラーではなく標準出力（stdout）を用いるように統一（Task Scheduler/cron での取り扱いを想定）。
- 起動スクリプト（monitoring / execution）でプロセス優先度を最初に "high" に設定するように統一。

### Fixed
- 環境変数パーサの堅牢化:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善。
- MONITOR_POLL_INTERVAL の無効値（0以下や非整数）の場合にデフォルトにフォールバックし、警告ログを出すように変更。
- process_priority と CPU affinity で権限や未対応 OS の扱いを安全に（ログ警告で）回避するように実装。
- position_sizing にて:
  - lot_size 単位での丸め、per-stock 上限・aggregate cap 適用、cost_buffer の考慮、残余キャッシュでの再配分ロジックを導入し過投資を防止。

### Security
- config_setup の保存前表示ではシークレット値はマスク表示（****）して露出を防止。
- .env 生成時に「.env を Git にコミットしないこと」を明示するヘッダを出力。

### Known issues / 注意点
- kabusys.research.factor_research.calc_momentum は実装途中（ファイル末尾が切れている等の状態）で、完全なファクター計算は未完成の可能性あり。研究関連コードは今後の拡張対象。
- position_sizing の price フォールバックに関する TODO コメントあり（価格欠損時の扱いで前日終値や取得原価のフォールバックが未実装）。
- monitoring はコード上「環境にかかわらず本番 sqlite_path を使用する」としているため、開発環境で監視 DB を分離したい場合は設定や実行方法に注意が必要。
- validate_config の YAML コンテンツ検証は PyYAML の有無に依存。PyYAML がない環境では YAML 内容検証はスキップされ、警告が出る。
- run_execution 内の BrokerClientFactory / ExecutionEngine などは実際のブローカークライアント実装に依存するため、paper_trading と live の動作差分は broker 実装に依存。

---

（この CHANGELOG はコードからの推測に基づき作成しました。実際の変更履歴やリリースノートと差異がある可能性があります。必要であれば、特定のコミットや差分に基づく厳密な CHANGELOG 作成を支援します。）