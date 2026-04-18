# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべてのバージョンは semver 準拠を意図しています。

## [0.1.0] - 2026-04-18

初回公開リリース。KabuSys のコア機能群、起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築ロジック、検証ツール類を追加。

### Added
- パッケージ基礎
  - パッケージ初期化およびバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止を実装。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
    - duckdb との接続確立、監視 DB 初期化処理を統合。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用 DB（data/paper_trading.db）に完全分離して記録。
    - 停止フラグ・PID ファイルの取り扱いとデーモンスレッド方式でのエンジン実行制御を実装。
- 設定管理
  - config.py
    - 環境変数／.env の読み込みおよび Settings クラスを実装。
    - プロジェクトルート自動検出 (.git または pyproject.toml を基準) による .env 自動読み込み機能を追加。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 各種設定プロパティ（DB パス、API トークン、運用フラグ、閾値など）を提供し、値検証を行う。
    - paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
- 設定関連 CLI
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の入力補助と .env 書き出し機能。
  - validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、DB パス存在確認、YAML のパース検査（PyYAML がある場合）、
      本番環境向けガード（LINE 通知、Kill-Flag の自動クリア設定など）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合に等金額配分にフォールバックする警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別エクスポージャーを考慮して候補をフィルタ）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップとフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・合計投下上限（aggregate cap）スケーリング、コストバッファ考慮を実装。
    - 利用可能現金に応じたスケールダウンと端数（fractional remainder）処理の実装。
  - portfolio パッケージ __init__ で主要関数を公開。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数や引数から動的に設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - psutil による優先度設定と CPU affinity 固定機能を提供。失敗時は警告ログでスキップ。
- 監視・モニタリング DB 初期化
  - monitoring/monitoring_db.py（起動スクリプトから利用）により監視用テーブルの冪等な初期化を呼び出す導線を追加。
- Execution 実装の組み立て点
  - run_execution の内部で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てる流れを実装（リスク設定のデフォルトパラメータを含む）。
  - RiskManager の初期化に broker.get_available_cash() を用いて初期ポートフォリオ値を取得する実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite のログを集計し、稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を算出してレポート出力する CLI を追加。
    - デフォルト閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - 日付フィルタ（--from, --to）と DB パスの指定（--db / 環境変数）に対応。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - モメンタム等のファクター計算インフラを追加（DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計）。モメンタム計算の実装が開始されている（ファイルの一部まで実装）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Notes / Implementation details
- 環境分離
  - Paper Trading は実運用 DB と明確に分離されるよう設計（settings.is_paper による sqlite_path 切替）。
- フォールバックと堅牢性
  - .env のパースルールはクォートやエスケープ、インラインコメントに対応しており、OS 環境変数を保護する仕組みを持つ。
  - ログディレクトリ作成失敗、プロセス優先度設定失敗、duckdb/sqlite の操作失敗などは例外で全面終了させず、警告や例外ログを残して安全に継続する設計。
- 設定検証
  - 起動前に validate_config.py を用いて環境不備を検知することを推奨。--strict モードで警告を失敗扱いにできるため、本番導入前の確認が容易。

次回以降のリリースでは、ExecutionEngine / BrokerClient 実装詳細、monitoring の SystemMonitor 実装、factor_research の完全実装、テスト・ドキュメント整備、エラーハンドリング改善等を計画しています。