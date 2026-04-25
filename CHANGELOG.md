# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py: 0.1.0）に基づきます。

## [0.1.0] - 2026-04-25

### Added
- 初期リリース: KabuSys — 日本株自動売買システムの基本モジュール群を追加。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知して安全にループ終了。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient と paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 停止フラグ (data/stop_requested.flag) 検知でエンジン停止。実行 PID を data/execution.pid に記録する想定。
- 設定管理:
  - config.py
    - .env / 環境変数自動ロード機能（.env, .env.local）を実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
    - 詳細な .env パーサ実装（export 形式、クォートやエスケープ、インラインコメントの扱いに対応）。
    - Settings クラスで各種設定（DB パス、API トークン、監視閾値、環境判定フラグ等）をプロパティとして提供。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 設定ユーティリティ / CLI:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加（python -m kabusys.config_setup）。
    - 出力時に .env に書き込むテンプレートを整備し、機密値はマスク表示。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性をチェックする CLI（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群、DB未依存）:
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート/上位選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが0のとき等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防ぐための候補フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を定義、未知値はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の割当方式に基づく発注株数計算、単元（lot）丸め、aggregate キャップ調整、コストバッファ考慮。
- 研究用モジュール:
  - research.factor_research（モメンタム等ファクター計算の骨格を追加。DuckDB を使った prices_daily/raw_financials ベースの計算を想定）
    - モメンタム、MA200乖離、ATR、出来高指標などの計算方針を実装（関数 calc_momentum 等の実装開始）。
- ツール:
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（期間フィルタ・DB指定オプションあり）。
    - 指標/閾値を定義し、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH を上書き可）。
- ログ・プロセスユーティリティ:
  - utils.logging_setup
    - setup_logging 関数を追加。stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils.process_priority
    - set_process_priority / set_cpu_affinity を追加。Windows/Linux の差分を抽象化し、アクセス権限エラー時に安全に警告してスキップ。
- 監視 DB 初期化フック:
  - monitoring.monitoring_db.init_monitoring_db を実行して監視テーブルが存在することを保証（冪等）。
- パッケージ初期化:
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定、主要サブパッケージを __all__ に追加。

### Changed
- n/a（初期リリースのため既存からの変更はなし）

### Fixed
- n/a（初期リリース）

### Notes / Behavior details（重要な挙動）
- run_monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用する設計になっているため、監視データは本番 DB に書き込まれる点に注意。
- run_execution は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する。
- .env の自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- config_setup による .env は機密情報を含むため絶対に Git にコミットしないことを README 等で注意喚起する想定（ファイルヘッダにもその旨を出力）。
- MONITOR_POLL_INTERVAL に不正な値（整数でない、1 未満など）を設定した場合、デフォルト 60 秒にフォールバックして警告ログを出力する。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム非対応時に警告ログを出力してスキップする安全設計。

### Configuration / Environment variables（主なもの）
- 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- 動作環境: KABUSYS_ENV (development | paper_trading | live) — Settings.env により判定
- DB:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- ログ: LOG_LEVEL, LOG_DIR
- 監視: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 監視ループ間隔: MONITOR_POLL_INTERVAL（run_monitoring 用、デフォルト 60）
- Paper Trading:
  - PAPER_FILL_MODE (instant | partial | never | reject)

### Migration / Upgrade notes
- 既存プロジェクトから導入する際は .env を本ツールの config_setup で作成/確認し、validate_config で必須環境変数やパスを検証してください。
- 監視系を導入する場合、run_monitoring が本番 sqlite_path を直接使用する点を理解し、監視データを本番 DB に格納して問題ないか確認してください。ペーパートレード用の分離は run_execution の実装で対応しています。

---

今後のリリースでは、Strategy/Execution の実装詳細（Engine の内部処理、Broker 実装、monitoring/system_monitor の詳細）、テストカバレッジ・ドキュメント（PortfolioConstruction.md など）の反映、config の追加検証やエラーハンドリング強化を予定しています。