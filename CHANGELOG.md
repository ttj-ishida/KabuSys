# CHANGELOG

すべての重大な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。KabuSys のコアユーティリティ、実行監視、ポートフォリオ構築、検証ツール群を追加。
- 実行関連スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV により paper_trading モード時は MockBrokerClient を使用し、ペーパートレード専用 DB（data/paper_trading.db）に完全に分離して記録。PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止、スレッド監視を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）。監視用 DB は環境に関係なく本番 sqlite_path を使用。停止フラグ検出でループ終了。
- 設定管理
  - config.py: .env/.env.local の自動読み込み（プロジェクトルート検出ベース）、柔軟な .env 行パーサ（export、クォート、インラインコメントの処理）、環境変数の取得ラッパ（Settings クラス）を実装。各種設定（DB パス、ログレベル、閾値、paper_trading 用オプション等）をプロパティで提供。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。シークレット項目のマスク、デフォルト、選択肢、保存の確認機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、DB パスの親ディレクトリチェック、YAML パース検証（PyYAML がある場合）、KABUSYS_ENV=live に対するガードチェック、--strict モード（警告を FAIL 扱い）をサポート。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。StreamHandler（stdout）と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）を設定、ログディレクトリ作成の失敗を安全に扱う。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足等で失敗した場合は警告にとどめる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選抜（select_candidates）、等配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を追加。スコアが全て 0 の場合のフォールバックを含む。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。unknown セクターの扱い、レジーム不明時のフォールバックを実装。
  - portfolio/position_sizing.py: ポジションサイズ計算（risk_based / equal / score 対応）、単元株（lot_size）での丸め、aggregate cap によるスケールダウンと残差配分ロジック、コストバッファの扱いなどを実装。
- データ・リサーチ
  - research/factor_research.py: DuckDB を利用したファクター計算フレームワークの雛形（モメンタム等の定数と calc_momentum 関数の骨子）を追加（処理途中のファイルあり）。
- 分析・検証ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。システム稼働率、注文成功率（Fill Rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。期間指定（--from/--to）、DB パスの指定（--db / 環境変数）をサポート。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部に公開すべきでない値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は .env に格納する設計とし、config_setup に注意喚起を記載（.env を Git にコミットしない旨）。ログは標準出力とファイルに記録するが、機密情報のログ出力に注意すること。

---

注記:
- run_monitoring と run_execution はともに起動時にプロセス優先度を "high" に設定しようと試みます（権限不足の場合は警告で続行）。
- run_monitoring は監視 DB 初期化のため sqlite3 接続を行い、duckdb も併用します。monitoring 用 DB 初期化は init_monitoring_db による冪等処理を行います。
- run_execution の RiskManager 初期設定にはデフォルト値（max_position_pct=0.20 等）が埋め込まれていますが、将来的には外部設定（yaml 等）での上書きを想定しています。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルを想定しており、外部 API には依存しない設計です。

今後の予定（例）:
- factor_research の完成、Strategy 実装・統合、YAML ベース設定のロード、より詳細なテスト・ドキュメント整備。