CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
（注: 以下はソースコードの内容から推測して作成した変更履歴です）

Unreleased
----------

### Added
- 監視/実行サブシステムの起動エントリスクリプトを整備
  - run_monitoring: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag で制御。
  - run_execution: ExecutionEngine の起動。スレッドでセッションを実行し、停止フラグで優雅に終了可能。実行 PID を data/execution.pid に保存（Engine 側で利用）。

- Paper Trading 対応の分離
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用いる設計に対応。
  - paper_trading 用 SQLite データベース（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離。

- 設定管理・ウィザード・検証ツール
  - config.Settings: 環境変数をラップしたプロパティ群を提供（DB パス、各種閾値、PAPER_FILL_MODE 等を含む）。
  - config_setup: 対話式 .env 作成/更新ウィザードを追加（.env の読み書き、シークレットマスク表示など）。
  - validate_config: 起動前に .env および config/*.yaml の妥当性チェックを行う CLI を追加。--strict オプションで警告をエラー扱いに可能。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: stdout への StreamHandler および日次ローテーション (TimedRotatingFileHandler) をルートロガーに一元設定。ログディレクトリの作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity を設定する set_cpu_affinity も提供。起動スクリプトで優先度を高に設定する呼び出しを追加。

- ポートフォリオ構築関連の純粋関数群（DB 非依存）
  - portfolio.portfolio_builder: シグナルの候補選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 各銘柄の発注株数算出ロジック（risk_based / equal / score）、単元株（lot_size）での丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的計算。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。

- Paper Trading 検証レポートツール
  - tools.paper_verification_report: SQLite のペーパートレードログから各種指標（稼働率、注文成功率、送信率、レイテンシ P95 など）を集計してレポート出力する CLI を追加。閾値に基づく PASS/FAIL 判定、--from/--to/--db オプションをサポート。

### Changed
- .env 自動ロードの強化
  - プロジェクトルートを .git または pyproject.toml を基準に探索して自動で .env/.env.local を読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env のパースは export プレフィックス・クォート・エスケープ・コメント処理に対応（堅牢化）。

- DB 接続方針
  - 監視系は環境にかかわらず本番 sqlite_path を使用する旨を明示（run_monitoring）。
  - 実行系は KABUSYS_ENV に応じて paper_sqlite_path を使うことで paper_trading と本番 DB を分離（run_execution）。

- ログ設定のデフォルト・挙動を統一
  - LOG_LEVEL / LOG_DIR の解決順やハンドラ再設定（既存ハンドラの flush/close → 削除）を明確化。

### Fixed
- エントリポイントの安全な終了処理
  - run_monitoring/run_execution での接続クローズ処理を finally ブロックにて保証。

### Security
- .env の生成スクリプトに対し「.env を絶対に Git にコミットしないこと」を明示するヘッダーを追加。

### Removed / Deprecated
- なし（現時点で明示的な削除・非推奨は確認されず）

### Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価をフォールバック価格として用いる検討が記載されている（TODO）。
- research.factor_research モジュールは実装途中である箇所が存在（末尾が途中で切れている）。ファクター計算ロジックの完成・テストが必要。

[0.1.0] - 2026-04-22
--------------------

### Added
- 初回公開相当の機能群を実装（監視・実行エンジン、設定管理、ログ/プロセスユーティリティ、ポートフォリオ構築、検証ツール）
  - システム監視: SystemMonitor のポーリングループ起動スクリプト（run_monitoring）
  - 実行エンジン: ExecutionEngine 起動スクリプト（run_execution）、BrokerClientFactory によるブローカークライアント生成（paper_trading 用 Mock 対応）
  - 設定管理: Settings（環境変数ラッパー）、対話式 .env ウィザード（config_setup）、設定検証 CLI（validate_config）
  - ロギング: 統一的なログ設定ユーティリティ（stdout + 日次ローテーション）
  - プロセス制御: プロセス優先度・CPU affinity 設定ユーティリティ（utils.process_priority）
  - ポートフォリオ: 候補選定、重み計算、セクター制限、レジーム乗数、株数決定アルゴリズム（lot 丸め、aggregate cap 等）
  - モニタリング DB 初期化ユーティリティの使用
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）

### Changed
- .env の自動読み込みをプロジェクトルート基準で行うように（.env, .env.local）。既存の OS 環境変数は上書き対象外（protected）。
- 実行系は paper_trading 用 DB を使用することで本番 DB から完全分離。

### Fixed
- 起動/停止時に DB 接続を必ず close するように修正（finally ブロックでのクローズ保証）。

### Known issues / TODO
- factor_research モジュールが未完（実装継続中）。
- 一部価格欠損時のフォールバックロジックが未実装（price が 0.0 の場合の扱いに注意）。

メンテナンス情報
-----------------
- バージョンはパッケージの __version__ に合わせて 0.1.0 を設定しています。
- 重要な環境変数:
  - KABUSYS_ENV: development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
  - PAPER_FILL_MODE: instant | partial | never | reject
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB のパス（tools.paper_verification_report / run_execution）
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存（失敗時は stdout のみ）。

もしこの CHANGELOG に追加してほしい点（リリース日を変更、カテゴリ追加、より詳細な変更点の追記など）があれば教えてください。