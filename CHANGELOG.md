# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 日付はソースから推測して記載しています。必要に応じて調整してください。

## [Unreleased]

### Added
- リポジトリの初期機能群を追加（初回リリース準備）。
  - 自動売買エンジン用の起動スクリプト:
    - run_execution.py — ExecutionEngine の起動/監視ループ、スレッドでの実行、停止フラグ監視、ペーパートレード時の専用 DB 分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - run_monitoring.py — SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 設定管理:
    - config.py — 環境変数/.env の自動読み込み機能、.env/.env.local の優先度管理、プロジェクトルート検出ロジック、各種設定値（DB パス、API トークン、監視閾値、環境種別など）を Settings クラスで提供。
    - config_setup.py — 対話式ウィザードで .env を作成/更新する CLI。必須項目／任意項目の定義とファイル出力をサポート。
    - validate_config.py — .env と config/*.yaml の事前検証 CLI。--strict オプションで警告も失敗として扱う。
  - モニタリング／初期化:
    - run_* スクリプト内で init_monitoring_db を呼び、監視用テーブルが存在することを保証（冪等）。
  - ペーパートレード検証ツール:
    - tools/paper_verification_report.py — Paper Trading のログ（SQLite）から稼働率、注文成功率、送信率、レイテンシ（P95 含む）等を集計し PASS/FAIL 判定するレポート生成 CLI。閾値の定義と期間フィルタ、DB パスの CLI/環境変数指定をサポート。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）:
    - portfolio/portfolio_builder.py — シグナル選定（スコア降順）、等分配/スコア加重配分。
    - portfolio/position_sizing.py — 発注株数計算（risk_based / equal / score 対応）、単元株丸め、aggregate cap によるスケールダウン、手数料・スリッページ緩衝（cost_buffer）。
    - portfolio/risk_adjustment.py — セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/__init__.py でエクスポートを整備。
  - 研究用モジュール:
    - research/factor_research.py — DuckDB を使ったファクター計算（Momentum: 1M/3M/6M, MA200乖離、Volatility: ATR20、流動性指標等）。データ窓や欠損ハンドリングを設計に盛り込む。
  - ユーティリティ:
    - utils/process_priority.py — Windows/Linux/macOS の差を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。権限不足や未対応環境に対するフォールバック/警告ログを実装。
  - パッケージ基礎:
    - __init__.py にバージョン（0.1.0）を追加。

### Changed
- .env の読み込み仕様を改善:
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出することで、作業ディレクトリに依存しない読み込みを実現。
  - .env のパースロジックで以下をサポート／堅牢化:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（スペースやタブに応じてコメントを判定）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用）。
  - .env.local を .env の後にロードし、OS 環境変数を保護しつつ上書き可能にした（protected set の導入）。

### Fixed
- run_execution/run_monitoring のリソース管理を改善:
  - ループ終了時に sqlite3/duckdb 接続を finally ブロックで確実にクローズするように修正。
  - 停止フラグ（data/stop_requested.flag）検知による優雅な停止処理を実装。
  - run_execution で既に停止フラグが立っている場合は起動を回避。

### Security
- .env の自動生成ウィザードで生成されるテンプレートに「.env を絶対に Git にコミットしないこと」の注意書きを明記（config_setup.py）。

---

## [0.1.0] - 2026-04-18

初回公開リリース。上記の機能群をまとめてリリース。

- 主要機能:
  - 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 監視ループ起動スクリプト（run_monitoring.py）
  - 環境設定管理（Settings）、.env ウィザード（config_setup.py）、検証 CLI（validate_config.py）
  - Paper Trading レポート生成ツール（tools/paper_verification_report.py）
  - ポートフォリオ構築モジュール（portfolio/*）
  - ファクター計算モジュール（research/factor_research.py）
  - process priority / cpu affinity ユーティリティ（utils/process_priority.py）
  - パッケージメタ情報（__version__ = "0.1.0"）

- 既知の注意点（ドキュメントに明記）
  - run_monitoring は KABUSYS_ENV にかかわらず monitoring 用 DB として Settings.sqlite_path（本番パス）を使用する点に注意。
  - PAPER_FILL_MODE の値検証を行い、無効値は例外を送出する。
  - Settings.env / Settings.log_level は許容値以外を設定すると ValueError を送出する。
  - 一部ロジックは将来の拡張（銘柄別 lot_size、価格フォールバック等）を想定して TODO コメントを残している。

---

過去のバージョンや将来の変更はこのファイルに追記してください。