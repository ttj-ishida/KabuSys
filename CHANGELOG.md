CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現時点の差分は特になし。新規リリースに向けての変更はここに記載します。）

[0.1.0] - 2026-04-25
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本機能を実装。
- 起動スクリプト:
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。停止フラグ・PID ファイル連携とスレッド実行ロジックを実装。
- 設定管理:
  - config.Settings: 環境変数/ .env からの設定読み込みを提供。KABUSYS_ENV, LOG_LEVEL, DB パス、Paper Trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をプロパティとして公開。環境値の妥当性チェックを実装。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - config_setup CLI: 対話式ウィザードで .env を初期作成/更新するツールを追加。既存値読み込み・シークレットマスク表示・確認プロンプトを実装。
  - validate_config CLI: 起動前の設定検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の有無と（PyYAML があれば）パース検証、本番環境 guard（LINE 等）チェックを実装。--strict オプションで警告を FAIL 扱いにできる。
- ロギング/プロセス管理ユーティリティ:
  - utils.logging_setup.setup_logging: stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに統一設定。既存ハンドラの二重登録防止、ログディレクトリ解決・自動作成、環境変数/引数からのログレベル解決を実装。
  - utils.process_priority: set_process_priority と set_cpu_affinity を追加。Windows/Linux/macOS の差分を吸収し psutil を用いて優先度設定・CPU アフィニティ固定を試行。権限不足時は警告を出して安全にスキップ。
- データベース/分析:
  - DuckDB 接続サポート（Settings.duckdb_path）。起動スクリプトやエンジンで duckdb 接続を使用して分析用途に対応。
  - 監視 DB 初期化呼び出し（init_monitoring_db）を各起動シーケンスで行い、監視テーブルの存在を保証（冪等）。
- Execution コンポーネント組立て:
  - BrokerClientFactory によるブローカクライアント選定（paper_trading 時は MockBrokerClient 想定）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとデフォルト RiskConfig の採用（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等比重（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: 株数決定ロジック calc_position_sizes を実装。リスクベース/等分配/スコア配分の複数方式、単元株（lot_size）対応、手数料スリッページ考慮（cost_buffer）、aggregate cap によるスケールダウンと端数処理を実装。
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する閾値を定義。DB パスは引数/環境変数/デフォルトで解決。
- 研究モジュール（骨組み）:
  - research.factor_research: モメンタム等の計算ロジック（calc_momentum 等）開始。DuckDB の prices_daily / raw_financials を前提としてファクター計算を設計。

Changed
- デフォルト動作:
  - 監視（run_monitoring）は MONITOR_POLL_INTERVAL により動作間隔を調整可能。0 以下の不正値はデフォルトにフォールバックし、警告を出す実装。
  - run_execution は paper_trading モード時に DB を完全分離する設計へ（本番 DB と混ざらないように）。
- ロギング:
  - コンソール出力を stdout に統一（cron/task scheduler でのリダイレクト運用を想定）。
  - ログファイル保管は日次ローテーション、30 世代保持に設定。

Fixed
- 環境変数読み込み:
  - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント handling、空行/コメント行無視）。
  - .env 読み込み時の上書きルール（OS 環境変数保護）を明確化。
- 設定検証:
  - validate_config は PyYAML 未導入環境を考慮して YAML 検証をスキップし、適切に警告を出すようにした。
- レジーム/重み計算:
  - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックし、警告ログを出力するように改善。
- 頑健性:
  - process_priority / cpu_affinity 設定で権限不足や未対応 OS を許容し、警告ログでスキップする実装により起動失敗を防止。
  - run_monitoring/run_execution の終了処理で DB 接続を確実にクローズする finally ブロックを追加。

Known issues / Notes
- research.factor_research の実装は途中（ファイル末尾が切れている部分あり）。ファクター計算ロジックは引き続き実装・テストが必要。
- 単元株（lot_size）は現状全銘柄共通の引数で指定。将来的に銘柄ごとの lot_size を持つマスタ導入が想定されている（TODO コメントあり）。
- apply_sector_cap では price が 0.0 の場合にエクスポージャーが過少に見積られる懸念あり。前日終値や取得原価などのフォールバック価格導入が検討課題。
- ExecutionEngine / BrokerClientFactory, SystemMonitor 等の詳細実装はこの差分に含まれていることを想定しているが、外部モジュールの実装・挙動に依存する箇所があるため、統合テストを推奨。

メンテナンス
- 次のリリースでは以下を優先することを推奨:
  - research モジュールの完成とテスト
  - End-to-end テスト（paper_trading と live の切り替え、DB 分離、kill/stop フラグの動作確認）
  - エラーメトリクスとアラート（LINE 連携）の追加テスト
  - 銘柄毎 lot_size / 手数料モデルの拡張

----- 
この CHANGELOG は、提供されたコードベースの内容から実装意図・仕様を推測して作成しています。実際のコミット履歴や設計ドキュメントに基づくものではない点にご留意ください。