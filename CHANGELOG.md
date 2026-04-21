# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はコードベースの現在時点（2026-04-21）で推測して付与しています。実際のリリース日やバージョン運用に合わせて調整してください。

## [Unreleased]

### Added
- CLI / 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV による paper_trading モードをサポートし、ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用する分離設計を導入。停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）、停止フラグ検出でグレースフル終了。
  - validate_config.py: .env および config/*.yaml のスタティック検証 CLI を追加。--strict モードで警告も失敗扱いに可能。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。必要項目のプロンプト、既存 .env の読み込み、保存処理を実装。
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を出力。

- ポートフォリオ構築ライブラリ（純粋関数）を追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes) を実装。risk_based / equal / score の割当方式、lot_size 単位での丸め、aggregate cap によるスケーリング、コストバッファ考慮などをサポート。
  - portfolio パッケージのエクスポートを整備。

- 設定関連・ユーティリティ
  - config.py: プロジェクトルートを自動検出して .env 自動読み込みを実装（.env / .env.local、既存 OS 環境変数の保護）。細かい .env パース（export、クォート、エスケープ、インラインコメント処理）に対応。Settings クラスで各種環境変数プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PID ファイルパス、各種しきい値等）を提供。
  - utils/logging_setup.py: 統一的なロギング初期化を提供。コンソール（stdout）と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) を設定し、既存ハンドラの二重登録を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows と POSIX の対応、例外時は警告でスキップ）。CPU affinity 設定関数も提供。
  - monitoring.monitoring_db 初期化呼び出しを各スクリプトで行うことで監視テーブルの存在を保証。

- データベース / 分析
  - DuckDB の接続を各エンジンで受け渡す実装（duckdb.connect を利用）。分析用 DB（data/kabusys.duckdb）を想定。

### Changed
- ペーパートレードと本番 DB の明確な分離
  - Execution 起動時に settings.is_paper を参照して paper_sqlite_path を使用するように変更（本番 monitoring DB と完全分離）。
- ログ出力とディレクトリ解決の挙動改善
  - ログレベルは引数・環境変数・デフォルトの順で解決。ログディレクトリ作成失敗時に安全にフォールバックする挙動を追加。
- 設定検証の強化
  - validate_config.py において必須環境変数チェック、KABUSYS_ENV の検証、YAML パーサの有無を考慮したファイル検証、KILL_FLAG 関連の本番ガード等を追加。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パーサのクォートおよびエスケープ処理やインラインコメントの扱いを改善し、より実運用向けの .env 設定に耐えるように修正。
- プロセス優先度設定の例外ハンドリング強化
  - 権限不足や未サポート OS での失敗時に警告でスキップするようにして、起動失敗しないように修正。

### Notes / Known issues
- research/factor_research.py の実装は途中で切れている（ファイル末尾が不完全）。ファクター計算群（モメンタム等）の実装は開始されているが、未完了の箇所が存在するため、本番使用前に補完が必要。
- 一部 TODO コメントあり（例: position_sizing の lot_size を銘柄別に拡張する等）。将来拡張の余地あり。

---

## [0.1.0] - 2026-04-21

初回公開相当のリリース（コードベースの現状から推測）。上記 Unreleased の多くの機能群が本バージョンで導入された想定。

### Added
- 基本モジュール群の提供
  - 実行および監視の起動スクリプト（run_execution, run_monitoring）
  - 環境設定管理（config.py）と対話式ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - ロギング・プロセス優先度ユーティリティ（utils.logging_setup, utils.process_priority）
  - ポートフォリオ構築ライブラリ（portfolio.*: 候補選定・重み計算・リスク調整・株数算出）
  - Paper Trading 検証レポートツール（tools.paper_verification_report）
  - DuckDB / SQLite を使ったデータ接続比定と初期化呼び出し

### Changed
- ペーパートレード用 DB を分離（PAPER_TRADING_SQLITE_PATH の導入）
- モニタリング DB は環境に依らず本番 sqlite_path を使用する仕様を明記

### Fixed
- .env の自動読み込み時の上書き制御（OS 環境変数保護）を導入
- ログハンドラの重複登録を防止し、ファイル出力失敗時のフォールバックを実装

---

（注）この CHANGELOG は、提供されたソースコードから機能追加・変更点を推測して作成しています。実際のコミット履歴やリリースノートに基づく正確な履歴作成が必要な場合は、Git のコミットログやリリースタグ情報を元に調整してください。