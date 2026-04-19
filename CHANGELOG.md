# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内の現在のコードベースから推測して作成した変更履歴です（実装から読み取れる機能追加・改善・修正の要約）。日付はこのスナップショットを元に設定しています。

## [Unreleased]
- 将来の変更をここに記載

## [0.1.0] - 2026-04-19
初回公開リリース（推測）。日本株自動売買システム「KabuSys」のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、設定管理および補助ツールを含む。

### Added
- 基本パッケージとバージョン情報
  - package metadata: `__version__ = "0.1.0"` を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを実装。環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て・起動ロジック。
    - PID ファイル管理、stop フラグ（data/stop_requested.flag）による安全な停止処理。
  - run_monitoring: SystemMonitor をポーリングで実行する監視用スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグによる安全停止、例外捕捉でループ継続。
- 設定管理
  - Settings クラスを導入し、環境変数からアプリケーション設定を統一的に取得。
    - J-Quants / kabuステーション / LINE API / DB パス / 監視・閾値などの設定をプロパティとして提供。
    - env（KABUSYS_ENV）や LOG_LEVEL のバリデーションを実装。
    - paper_trading 用設定（paper_sqlite_path、paper_fill_mode）をサポート。PAPER_FILL_MODE の値検証を実装（instant/partial/never/reject）。
  - 自動 .env 読み込み機構
    - プロジェクトルートを .git または pyproject.toml から探索して .env と .env.local を自動で読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パーサーは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護するための上書き制御（protected set）を実装。
- 設定支援ツール
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 多数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に設定。
    - .env の読み書きロジック（既存値の再利用、シークレットマスク、保存確認）。
  - validate_config: .env と config/*.yaml の内容検証ツールを提供。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、YAML ファイルの存在とパースチェック（PyYAML が利用可能な場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch に関する警告）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定するユーティリティを実装。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティを実装（psutil ベース）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS 時に安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等重・スコア重みの計算。全スコア 0 の場合は等重へフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき新規候補をフィルタ（unknown セクターは除外対象としない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・リスクパラメータに基づく発注株数計算（risk_based / equal / score の各方式をサポート）。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（スケーリング）を実装。余剰キャッシュで端数を lot 単位で配分するロジックを搭載。
- リサーチ / ファクター計算（骨組み）
  - research.factor_research: DuckDB 接続を利用したモメンタム・ボラティリティ・バリュー等のファクター計算モジュールの実装を開始（calc_momentum の骨子と定数を含む）。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成するスクリプトを実装。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定を行う閾値を定義。
    - 日付フィルタ（--from / --to）対応、DB パス指定 (--db) 対応。
- 監視関連
  - monitoring_db 初期化・SystemMonitor 呼び出しロジックを run_* スクリプトで使用（監視テーブルの冪等初期化）。

### Changed
- ログ出力の統一
  - 全起動スクリプトから logging_setup.setup_logging を呼び出すようにしてログの一貫性を確保（コンソール stdout とファイルの二重出力）。
- DB パスの取り扱い
  - paper_trading 環境では paper_trading 用 SQLite を利用し、本番 DB と完全分離する設計に変更（Execution 起動時）。
- 環境変数ロードの順序と保護
  - OS 環境変数を保護しつつ .env / .env.local を適切な優先度でロードする挙動を明確化。

### Fixed
- 設定パースの堅牢化
  - .env パーサーがクォート・エスケープ・inline コメント・export 形式を正しく処理するよう改善（空行・コメント行のスキップ等）。
- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL に 0 以下や不正値が指定された場合、ログに警告を出してデフォルト（60 秒）にフォールバックする処理を追加（time.sleep に不正値渡しによる例外回避）。
- リカバリ性の向上
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げてもループを継続するように例外捕捉とログ出力を追加。
- process_priority の非致命化
  - 権限不足や未対応 OS での例外を警告ログに落とし込み、起動失敗につながらないよう変更。

### Security
- 機密情報の取り扱い
  - config_setup ではシークレット項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE トークン）をマスクして表示。`.env` ファイルを絶対に Git にコミットしない旨の注意を追記。

### Notes / Implementation details
- 依存:
  - psutil（プロセス優先度 / CPU affinity）、duckdb、sqlite3、PyYAML（検証用。ない場合は YAML 検証をスキップ）等が必要。
- 設計方針:
  - 多くのモジュールは「DB に書き込まない純粋関数」設計になっており、テスト容易性を重視している。
  - paper_trading と live を明確に分離することで本番操作の安全性を確保。
  - ロギングは stdout を基準にしつつファイル出力を補助する構成。cron/Task Scheduler 等からの起動を意識して stdout に出力するよう設計。

---

（注）この CHANGELOG は与えられたソースコードから実装内容を推測して作成したものであり、実際のコミット履歴やリリースノートと完全に一致するとは限りません。必要であれば、さらに詳しい変更点（個別関数の振る舞い、未完成箇所の TODO 等）を抽出して追記できます。希望があれば対応します。