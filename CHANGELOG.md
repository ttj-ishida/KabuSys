CHANGELOG
=========

すべての注目すべき変更は Keep a Changelog のフォーマットに従って記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築、検証ツール群を導入。
- 実行・監視系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。BrokerClientFactory によりペーパートレード時に MockBrokerClient を利用する設計を導入。停止フラグ（data/stop_requested.flag）検知による安全停止、実行中 PID ファイル出力対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する動作を明確化。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスを実装。.env/.env.local の自動読込機能（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）、.env パースの強化（export プレフィックス対応、クォート/エスケープ処理、インラインコメントの扱い）、各種プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / 各種閾値等）を提供。KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。シークレット項目はマスク表示して入力を促し、.env ファイルを書き出す機能を持つ。
  - validate_config.py: 起動前検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。必須環境変数チェック、KABUSYS_ENV の検証、DB パスや config/*.yaml の存在確認、PyYAML 未インストール時のスキップ/警告、本番環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）などを実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中上限チェック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック動作を追加。
  - portfolio.position_sizing: 各銘柄の発注株数算出（risk_based / equal / score の allocation_method 対応）、単元株丸め、1 銘柄上限や aggregate cap（利用可能現金に応じたスケーリング）、コストバッファ考慮などのロジックを実装。lot_size に基づく再配分ロジックも含む。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 世代保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを追加。Windows / POSIX (Linux/Mac/FreeBSD) を吸収し、set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限制約時は警告を出してスキップする安全策あり。
- モニタリング / DB 初期化
  - monitoring.monitoring_db (参照): 起動時に監視用テーブルを冪等に初期化する init_monitoring_db の利用を統合。
  - SystemMonitor（run_monitoring からの利用）により定期的な system_status 記録等を想定した設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ（--from / --to）、データベース指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。P95 算出ユーティリティ、SQL クエリ群を含む。
- リサーチ（断片的）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity 設計方針） — DuckDB 経由で prices_daily / raw_financials を参照してファクターを計算する想定。モメンタム (1M/3M/6M 等)、MA200 乖離などの計算ロジックを含む（実装途中ファイルあり）。

Changed
- ログ出力の統一
  - 全起動スクリプトは setup_logging を使用して統一的にログを出力。StreamHandler は stdout を使用することで外部スケジューラとの相性を考慮。
- .env 自動読み込みの挙動
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込みする設計。OS 環境変数は上書き保護される（protected keys）。
- 実行 / 監視の安全ガード
  - 停止フラグ（data/stop_requested.flag）を用いたプロセス停止、PID ファイルの出力、KILL フラグや起動時クリア設定のチェックなどの安全ガードを盛り込んだ。

Fixed
- 環境変数・設定の堅牢化
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）に対して、警告を出してデフォルトにフォールバックする処理を追加。
  - .env パーサーの強化により、クォート文字列内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを適切に処理。これにより .env の記述ゆれに対してより寛容になった。
- DB 初期化の冪等性
  - Execution 起動時に監視テーブルの初期化を呼び出し、監視テーブルが存在することを保証する（init_monitoring_db を呼ぶことで安全に起動できるように）。

Notes / Breaking changes / Warnings
- セキュリティ: .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダに注意文を追加）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を特に確認すること。validate_config は本番向けの追加警告を出します。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" に限定。無効値は起動時に ValueError を発生させる。
- run_monitoring は監視用 DB に settings.sqlite_path（本番 sqlite_path）を常に使用するため、監視データは環境に依存せず一箇所に蓄積されます。必要があれば設定の見直しを検討してください。

Acknowledgments
- このリリースはプロジェクトの初期基盤（設定管理、ログ・プロセス管理、実行/監視インフラ、ポートフォリオ構築ロジック、検証ツール）を提供します。今後、strategy/ execution の詳細な実装や factor_research の完全実装、テストカバレッジ強化を予定しています。