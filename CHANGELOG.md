# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 日付は 2026-04-18（コード解析時点）を使用しています。
- バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - プロセス優先度を高に設定（set_process_priority）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止用フラグ（data/stop_requested.flag）/ PID ファイル（data/execution.pid）に対応し、外部からの停止を検知して安全にシャットダウン。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグファイルの検出によるループ停止処理、例外時のログ出力と継続動作に対応。
- 設定・環境管理:
  - config.py
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml 基準）。読み込み順: OS 環境 > .env.local > .env。
    - オーバーライド保護（既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env パースを堅牢に実装（export プレフィックス、クォート内エスケープ、インラインコメントの扱い等）。
    - Settings クラスを提供し、様々な設定プロパティ（DB パス、API トークン、紙取引設定、監視閾値、環境種別検証など）を取得・検証できるようにした。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。
  - config_setup.py
    - 対話式の .env ウィザードを実装。既存値の読み込み、シークレット項目のマスク表示、保存の確認などを実装。
- 設定検証 CLI:
  - validate_config.py
    - .env および config/*.yaml の存在と基本的妥当性をチェックする CLI。
    - 必須環境変数チェック、KABUSYS_ENV のチェック、LOG_LEVEL チェック、DB パスの親ディレクトリチェック、PyYAML が存在する場合は YAML のパース検証を行う。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番環境向けの追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の警告など）。
- ロギングユーティリティ:
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。
    - stdout（StreamHandler）を標準出力に出す設計（cron/Task Scheduler での扱いを考慮）。
    - 日次ローテーションの TimedRotatingFileHandler を logs/<app_name>.log に設定（30日分保持）。ログディレクトリ作成失敗時はファイル出力をフォールバックしてコンソール出力のみで継続。
- プロセス優先度 / CPU affinity ユーティリティ:
  - utils/process_priority.py
    - set_process_priority(level)（high/normal/low）を実装。Windows と POSIX(Linux/Mac/FreeBSD) を吸収する実装。
    - set_cpu_affinity(cpu_count) による CPU 固定機能を追加。権限不足や未対応環境は警告してスキップ。
- ポートフォリオ構築関連機能:
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点時は signal_rank でブレーク）で候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。sell_codes（当日売却予定）を除外して既存ポジションのエクスポージャーを計算。未知セクター("unknown") は上限対象外。
    - calc_regime_multiplier: market regime に応じた乗数を返す（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告を出して 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出を実装。
    - 単元株（lot_size）丸め、銘柄毎・総合キャップ（max_position_pct / max_utilization）を適用。
    - cost_buffer を考慮した投下資金の保守的見積もりと、利用可能現金を超えた場合のスケーリングおよび残余配分ロジックを実装。
- データツール / レポート:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等を算出して PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで --db/--from/--to を指定可能。
    - P95 計算や欠測時のハンドリングを実装。
- 研究用ファクター計算モジュール（research/factor_research.py）を追加（モメンタム等の指標算出の設計・一部実装を含む）。
- その他:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を起動スクリプトで一貫して実行。

### Changed
- （初回リリースのため履歴上の変更はなし。設計注意点をドキュメント内に明記）
  - ロギング: stdout を優先して出力する方針を採用（stderr ではない）。ファイル出力失敗時はフォールバックで継続する設計。

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- 秘匿情報取り扱い:
  - config_setup の対話でシークレット項目はマスクして表示。
  - .env 生成時に .env を誤ってコミットしない旨の注記を挿入。

### Internal / Notes
- 設定や DB パスのデフォルトは開発フレンドリーに data/ 配下を使用（DUCKDB_PATH, SQLITE_PATH 等）。
- Settings での検証は厳格だが、運用環境での値誤設定に対して明示的に例外や警告を出すことで早期検出を狙っている。
- 一部の機能（例: factor_research 内の関数実装の続き、将来的な lot_size の銘柄別対応、価格フォールバック等）は TODO コメントが残っているため、今後の改善ポイントとして扱う。

---

参照:
- 各モジュールの詳細な挙動はソースコードの docstring / コメントを参照してください。