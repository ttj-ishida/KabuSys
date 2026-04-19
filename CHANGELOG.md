# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  
リリースは semver を想定しています。

## [Unreleased]

### Added
- 全体
  - プロジェクト初期実装の記録（コア機能群、ユーティリティ、CLI、ツール群を追加）。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、専用 PID ファイル、停止フラグ検出、別スレッドでエンジンを起動する実装を提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグでの安全終了処理をサポート。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加。--strict オプションで警告をエラー扱いにできる。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加（期間指定・DB 指定オプション対応）。
- 設定管理
  - config.py: 環境変数の自動読み込み (.env/.env.local)、柔軟な .env パース（export, 引用符, インラインコメント対応）、Settings クラスによる設定アクセスを実装。実行環境 (development/paper_trading/live) の検証、paper_trading 用 DB パスや各種閾値等のプロパティを提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合のフォールバック警告を出力。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を追加。未知レジーム時のフォールバックと警告を実装。
  - portfolio.position_sizing: ポジションサイズ計算 (calc_position_sizes) を追加。risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリングロジック、手数料・スリッページの buffer を考慮。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。コンソール出力（stdout）と日次ローテートファイル出力を統一的に設定。環境変数や引数でログレベル・ログディレクトリを指定可能。
  - utils/process_priority.py: プロセス優先度（Windows の優先度クラス／POSIX の nice 値）および CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS 時に安全にスキップ。
- データベース / モニタリング
  - monitoring_db 初期化呼び出しを各起動スクリプトで保証（冪等にテーブルを作成）。
  - DuckDB 接続の統合（分析用 DB）を起動フローに追加。
- 研究 / ファクター計算（基礎実装）
  - research/factor_research.py: モメンタム等ファクター計算の骨組みを実装（DuckDB 接続を利用）。各種パラメータ定義と P95 算出ユーティリティ等を提供。

### Changed
- ロギング
  - すべての起動スクリプトで setup_logging を利用するよう統一し、ログ出力の一貫性を向上。
  - ファイルハンドラの作成失敗時にはコンソール出力のみで継続する堅牢性を実装。
- DB パスの分離
  - paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用するように変更し、本番 DB と完全に分離。
- 環境変数ロード順
  - 自動読み込み: OS 環境変数 > .env.local > .env の優先度で読み込む仕様とし、OS 環境変数は保護（上書き禁止）する挙動を実装。

### Fixed
- エラー耐性
  - run_monitoring.py のポーリング中に monitor.check_once() が例外を送出してもループを継続するよう例外捕捉とログ出力を追加。
  - 起動時に停止フラグが既にある場合、run_execution は起動を中止するよう変更（不要な起動防止）。
- .env パーサー
  - 引用符内のエスケープやインラインコメント処理、export プレフィックスを正しく処理するよう改良。

### Notes / Known issues
- research/factor_research.py は計算ロジックの骨格を実装中（コード末尾で未完の箇所あり）。完了・テストが必要。
- position_sizing.calc_position_sizes 内で価格欠損時のフォールバック処理が TODO コメントとして残っている（将来的な改善点）。
- process_priority の優先度設定は権限やプラットフォーム依存で失敗する場合があり、その場合は警告を出してスキップする実装になっています。

---

## [0.1.0] - 2026-04-19

初回公開リリース。

### Added
- 基本アプリケーション構成を初期実装。
  - 実行エントリ: run_execution.py, run_monitoring.py
  - 設定: config.py, config_setup.py, validate_config.py
  - ポートフォリオ構築: portfolio/* (builder, risk_adjustment, position_sizing)
  - ユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - 監視 / DB 初期化連携: monitoring_db 初期化呼び出しを統合
  - 分析用 DuckDB 統合
  - Paper Trading 向けツール: tools/paper_verification_report.py
  - 研究用: research/factor_research.py（骨格実装）
  - パッケージ初期化: __init__.py にバージョン 0.1.0 を設定

### Changed
- ロギング・プロセス管理の共通化により起動スクリプト間での一貫性を確保。
- 環境ごとの DB パス分離（paper_trading 用 DB の導入）。

### Fixed
- 起動 / 実行フローの安全性向上（停止フラグ検出、例外耐性、リソースクローズ処理）。

---

（備考）今後のリリースでは研究モジュールの完成、テストケース追加、運用向け監視（LINE 通知等）の強化、単体テストと CI 設定を予定しています。