# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。KabuSys の基本的な起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築ロジック、検証・ウィザード・レポートツールなどを追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用。
    - プロジェクト内 data/stop_requested.flag を検出して安全に停止。
    - duckdb と sqlite の接続確立とクリーンなクローズ処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行管理（デーモンスレッドで run_session を実行）。
    - 起動時・実行中に data/stop_requested.flag を検出して安全停止。
    - 実行プロセス用 PID ファイルパスをサポート。

- 設定管理
  - config.py: 環境変数と .env 自動読み込みロジックを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序（OS 環境変数を優先、.env.local は上書き可能）。
    - export KEY=val、クォート付き値、インラインコメントなどに対する堅牢なパーサ実装。
    - Settings クラスに各種プロパティ（DB パス、PID/kill flag、しきい値、環境判定、paper_trading 関連設定等）を提供。
    - PAPER_FILL_MODE のバリデーション、有効値チェック。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（項目定義・既存 .env 読み込み・書き込み機能）。
  - validate_config.py: 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース、live 時の追加注意点）。--strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑えるフィルタ（売却予定銘柄除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数算出。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）調整、cost_buffer を用いた保守的コスト見積り、スケーリングと残差分配の実装。

- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップして警告を出す。
    - 既存ハンドラの二重設定防止のためクリア処理を行う。
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。
    - アクセス権限や未対応 OS の場合は警告を出してスキップ。

- Tools
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status/trade_logs/risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計。
    - 基準値（稼働率 >= 99%、注文成功率 >= 90% 等）に基づく PASS/FAIL 判定を出力。
    - --from/--to/--db オプションをサポート。DB 未存在時のエラーメッセージを提供。

- Monitoring DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_monitoring/run_execution の起動フローに組み込み、監視用テーブルの存在を保証（冪等）。

- パッケージメタ
  - パッケージの __version__ を "0.1.0" に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- research.factor_research モジュールは設計と一部実装（定数など）を含むが、ファイル末尾で処理が途切れており（calc_momentum の実装が途中で終了）、完全実装は今後のリリースで対応予定。
- 一部の場所で価格欠損（price==0.0）を扱う TODO が残っている（price のフォールバック戦略など）。
- process_priority / set_cpu_affinity は権限や環境に依存する操作であり、AccessDenied や未実装環境では警告を出してスキップする設計。ただし運用環境での動作確認を推奨。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされる（テスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD を使用可能）。

### Security
- （初回リリースのため該当なし）

---

今後のリリースでは、research モジュールの完成、Strategy/Execution の追加テスト・ドキュメント強化、より詳細な監視・アラート設定の拡張を予定しています。