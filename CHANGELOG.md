# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

### Added
- ドキュメント化されたプロジェクト構成とバージョン管理（パッケージバージョン: 0.1.0）。
- 多数の起動スクリプト / CLI を追加:
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag によって行う。監視用 DB は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient による完全分離を行う。停止フラグおよび PID ファイルの取り扱いを実装。
  - validate_config.py: .env と config/*.yaml の設定整合性チェック CLI。--strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを提供。既存 .env の読み込み、シークレットのマスク表示、確認後の保存をサポート。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト。期間指定 (--from/--to) と DB 指定 (--db) に対応。稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）などを算出し、閾値判定（PASS/FAIL）を行う。

### Added (ライブラリ機能)
- config.Settings クラス:
  - .env の自動ロード（.env / .env.local、OS 環境変数保護。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - 各種環境変数の取得ラッパー（J-Quants / kabuAPI / DB パス / Paper Trading 関連設定 / 監視閾値 / ログ設定等）。バリデーション（列挙値チェック、必須項目チェック）を含む。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - paper_sqlite_path の分離（ペーパートレード時の DB 分離を想定）。

- ポートフォリオ構築用モジュール（pure functions、メモリ内計算）:
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレーク用 signal_rank による候補選定。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重（スコア合計が 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別の既存エクスポージャーを計算し、上限超過セクターの候補除外ロジック（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を決定（未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数決定ロジック。損失許容率、最大ポジション比率、lot_size（単元株）で丸め、cost_buffer を考慮した aggregate cap とスケールダウン・端数配分アルゴリズムを実装。

- utils:
  - logging_setup.setup_logging: stdout ストリームハンドラと日次ローテートする TimedRotatingFileHandler をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバック動作を実装。
  - process_priority:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度 (high/normal/low) を設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留め。未対応環境やアクセス権がない場合は警告でスキップ。

- 監視 DB 初期化フックを各起動スクリプトから呼び出すための init_monitoring_db（monitoring パッケージ内）呼び出しを統合。監視テーブルの存在を保証（冪等）。

- research.factor_research: ファクター計算モジュール（モメンタム、MA、ATR、出来高系等）を追加。DuckDB 接続を受け prices_daily / raw_financials テーブルから計算する設計。calc_momentum 等の関数骨格を用意（将来的な拡張余地あり）。

### Changed / Behavior
- 起動スクリプト全体で起動直後にプロセス優先度を "high" に設定する方針を採用（パフォーマンス想定）。
- run_monitoring は KABUSYS_ENV にかかわらず「監視 DB」として設定された sqlite_path（本番想定）を使用する明示的な挙動を記載。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離する動作を明示。
- .env パーサーはシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール、および export プレフィックスに対応する挙動を導入。

### Security / Reliability
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は Settings 経由で必須/任意を明確に管理。config_setup ではシークレットをマスク表示。
- validate_config により起動前に重要設定（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、YAML パース等）の事前検証を可能にし、本番環境設定ミスを検出しやすくした。

---

## [0.1.0] - 2026-04-11

初回リリース。上記の機能群を実装。

### Added
- 基本的なアプリケーション骨格とバージョン情報（__version__ = "0.1.0"）。
- 起動スクリプト: run_monitoring, run_execution。
- 設定管理: config.Settings、自動 .env ロード、.env パーサ。
- 設定ユーティリティ: config_setup（ウィザード）、validate_config（検証 CLI）。
- ロギング・プロセス制御ユーティリティ: logging_setup、process_priority（と CPU affinity サポート）。
- Portfolio モジュール（選定・配分・リスク調整・ポジションサイズ算出）。
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report）。
- 監視 DB 初期化フックの導入と起動スクリプトからの呼び出し。
- research.factor_research の骨格（ファクター計算用モジュール）。

### Notes / Known issues
- research.factor_research の一部関数は実装途中（calc_momentum の途中でファイルが終端）。今後追加実装が必要。
- 一部の挙動は環境依存（psutil による優先度設定やファイルシステムのパーミッション）。アクセス権限不足時は警告を出して処理を継続する設計。
- position_sizing の価格欠損時の挙動（price が欠損するとエクスポージャーが過少見積りされる旨の TODO コメント）に注意。

---

メンテナンス: 変更履歴は実装に合わせて更新してください。