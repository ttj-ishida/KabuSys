# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルでは主にソースツリーから推測される機能追加・改善点・バグ修正を日本語でまとめています。

なお、バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーションおよび CLI を追加
  - パッケージ名: KabuSys（日本株自動売買システム）
  - バージョン: 0.1.0

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI。
    - KABUSYS_ENV に応じて paper_trading モードなら専用の MockBrokerClient と分離された SQLite（data/paper_trading.db）を使用。
    - デーモンスレッドでエンジンを起動し、data/stop_requested.flag による停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - PID ファイル / 停止フラグの取り扱い（data/execution.pid, data/stop_requested.flag）。
    - Execution 用の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立て。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを抜ける。
    - 監視向け DB 初期化（監視テーブルの冪等初期化）と DuckDB 接続を行う。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と上書きポリシー（OS 環境変数保護）。
    - _parse_env_line により export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを正しく扱うパーサを実装。
    - 設定アクセスラッパー Settings を提供（各種環境変数の既定値、検証ロジックを含む）。
    - Paper Trading 用の別 SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - シークレット値はマスクして表示、デフォルト値の提示、選択肢の検証、書き出しテンプレートを提供。
    - 書き出し内容に注意喚起（.env をコミットしないこと等）。

  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在しない場合は警告）を実装。
    - --strict により警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティ。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、標準出力のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数を考慮した設定解決。

  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収したプロセス優先度設定。
    - set_process_priority(level) で high/normal/low を設定（アクセス権限不足等は警告を出してスキップ）。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能（未対応 OS や権限不足時は警告を出してスキップ）。

- ポートフォリオ構築モジュール（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank 使用）。
    - 重み計算 calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック・警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限チェック（sell_codes を除外、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear とフォールバック時の警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した発注株数計算。
    - 単元株（lot_size）丸め、銘柄単位・集合の上限（max_position_pct / max_utilization）適用。
    - cost_buffer を考慮した保守的なコスト見積り、available_cash 超過時のスケーリング処理（端数再配分ロジックあり）。

- 研究 / ファクター計算
  - research/factor_research.py（設計文書に従ったインターフェースを実装）
    - Momentum / Value / Volatility / Liquidity の計算を意図したモジュール構成（DuckDB 接続を受け取る設計）。
    - モジュールは prices_daily / raw_financials テーブルを参照する方針。
    - （ファイル末尾が途中で切れているため実装は継続が必要。）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツール。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ、リスク却下数 等を集計して評価 (PASS/FAIL)。
    - デフォルト DB パス: data/paper_trading.db。--db, --from, --to をサポート。
    - レポートの閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義。

- DB 関連
  - 監視用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）を併用する設計。
  - 監視 DB の初期化ユーティリティ init_monitoring_db を利用して起動スクリプト側で冪等にテーブルを保証。

### Changed
- ログ出力の統一
  - 全スクリプトで setup_logging を呼び出すように統一し、コンソールとファイル両方へ出力することで運用ログの一貫性を向上。

- 環境変数取り扱いの堅牢化
  - .env パーサ（_parse_env_line）を強化し、クォート・エスケープ・インラインコメント・export 形式に対応。
  - 自動ロード時に OS 環境変数を保護（protected set）して上書きミスを防止。

- 起動フロー改善
  - run_execution / run_monitoring ともに最初にプロセス優先度設定を行うようにして、起動直後のパフォーマンス安定性を改善。

- Paper Trading の分離強化
  - paper_trading モードでは専用 SQLite を使用し、本番データベースと完全分離する設計を明確化。

### Fixed
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring のポーリング間隔取得処理で、環境変数に不正（非整数、0 以下など）が指定された場合にデフォルトへフォールバックし、警告ログを出力するように修正。

- ログディレクトリ作成・ファイルハンドラ生成時の例外安全化
  - logging_setup でディレクトリ作成やファイルハンドラ生成に失敗した場合、コンソール出力のみで継続するようにして起動不能になる事態を回避。

- Process priority / affinity の権限・非対応 OS 耐性向上
  - utils.process_priority の例外処理を追加し、権限不足や未実装メソッド時に警告を出してスキップするようにした。

### Security
- .env の取り扱いに関する注意喚起を config_setup の出力に追加（.env を絶対に Git にコミットしないこと）。

### Notes / TODO
- research/factor_research.py の実装がファイル末尾で途中になっているため、残りの計算ロジック（SQL クエリや Z スコア正規化等）は継続実装が必要。
- position_sizing の価格欠損時（price が 0 または None）のフォールバックロジックが TODO コメントで残されている（前日終値や取得原価によるフォールバックを検討）。
- 設定ファイル（config/*.yaml）を用いた詳細設定の検証は PyYAML の有無に依存しているため、運用環境では PyYAML のインストールを推奨。

以上が、このリリース（0.1.0）で導入・変更された主要点のまとめです。運用手順や環境変数の例は config_setup と .env.example を参照してください。