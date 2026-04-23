# Changelog

すべての注記は Keep a Changelog の慣例に従います。  
このファイルはコードベースの現在の状態から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用する（data/paper_trading.db をデフォルト）。バックグラウンドスレッドでエンジンを実行し、data/stop_requested.flag による安全停止、実行時 PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループを終了。
- 設定関連
  - config.py: 環境変数・設定取得モジュール。自動 .env ロード（.env / .env.local、OS 環境変数を保護）、各種設定プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 関連など）を提供。PAPER_FILL_MODE の検証、paper_sqlite_path 等をサポート。
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読み込み、シークレットのマスク表示、.env の書き出しテンプレートを提供。
  - validate_config.py: 起動前チェック CLI。必須環境変数・KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース（PyYAML がある場合）などを検証。--strict オプションで警告を fail 扱いにできる。
- ポートフォリオ構築（純関数群、DB 非依存）
  - portfolio.portfolio_builder: シグナルの候補選定（select_candidates）、等金額重み（calc_equal_weights）、スコア加重（calc_score_weights、全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap: 当日売却対象を除外するオプションや "unknown" セクターの扱い）、市場レジームに応じた投下資金乗数（calc_regime_multiplier、未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式をサポート。単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的なコスト見積り、残余キャッシュを用いた端数配分ロジックを実装。
- 研究・ファクター
  - research.factor_research: Momentum / Value / Volatility / Liquidity などのファクター計算モジュールの骨組み（DuckDB の prices_daily / raw_financials を参照する設計）。モメンタム計算などの実装を含む（ファイル途中まで）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を使った DB 読み込み、稼働率・注文成功率・送信率・リスク却下数・レイテンシ（P95）を算出し PASS/FAIL 判定を出力。閾値はファイル内定義（稼働率 99% など）。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。stdout 出力 StreamHandler と日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーにセット。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows の優先度クラス / POSIX の nice 値を扱う）。CPU affinity 設定関数も提供（set_cpu_affinity）。

### Changed
- 監視動作・DB の扱いに関する設計決定を明示
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを記録（設計上の安全・一貫性確保のため）。
  - run_execution は paper_trading の場合に限り paper_sqlite_path を使用して本番 DB と完全分離。
- .env 読み込みの挙動強化
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。override と protected セットにより OS 環境変数の上書きを制御。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- ログ設定の取り扱い
  - stdout をデフォルトのコンソール出力に使用（cron 等のリダイレクトを想定）、既存ハンドラをクリアして二重出力を避ける。
- run_execution の起動フロー
  - broker factory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てを明確化。Engine はスレッドで稼働し、停止フラグ検知で安全停止を行う。リスク設定は RiskConfig でデフォルト値を設定し、初期ポートフォリオ値を broker.get_available_cash() から初期化。

### Fixed
- 環境変数 MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 数値変換失敗や 0 以下の値を渡された場合にデフォルト（60 秒）へフォールバックし、警告ログを出力するよう改善（run_monitoring）。
- process_priority / set_cpu_affinity の失敗耐性
  - 権限不足や未実装 API の例外を捕捉して警告を出すようにし、プロセスがクラッシュしないようにした。
- DuckDB/SQLite の接続ライフサイクル
  - run_monitoring / run_execution で finally により接続を確実に close するようにしてリソースリークを防止。
- paper_verification_report の統計計算で SQL が存在しない場合に OperationalError を捕捉して N/A を返すようにして耐障害性を向上。

### Security
- config_setup の対話式ウィザードでシークレット項目は表示時にマスクする実装（画面上の露出を低減）。
- .env テンプレート生成時に .env を絶対に Git にコミットしない旨のコメントを出力。

### Notes
- 一部モジュール（research.factor_research など）は設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）を参照する形で実装されており、DuckDB に依存する集計処理を行う設計です。必要なテーブル（prices_daily, raw_financials など）が存在することが前提です。
- config/ 以下の YAML ファイル（system_config.yaml など）はデフォルトでは生成されないため、validate_config では存在しない旨の警告が出ることがあります。scripts/generate_config.py（実装が存在する場合）で生成することを想定。

(将来的なリリースでは、テストカバレッジの拡充、Strategy/Execution の統合テスト、artifact 化された CLI の提供などを検討してください。)