# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。  

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初期リリース。

### Added
- 実行用スクリプト / エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）で完全に隔離して動作。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を参照する設計。
  - kabusys.validate_config: 起動前に .env と config/*.yaml の整合性をチェックする CLI。--strict オプションで警告も失敗扱いにできる。
  - kabusys.config_setup: .env を対話式に作成・更新するウィザード（対話式 CLI）。
  - kabusys.tools.paper_verification_report: Paper Trading 用の検証レポートを生成するスクリプト。期間指定や DB 指定可能で、稼働率・注文成功率・送信率・レイテンシ（P95）などを評価し PASS/FAIL を判定。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: position sizing ロジック（calc_position_sizes）。allocation_method に "risk_based" / "equal" / "score" をサポートし、lot_size 単位丸め、コストバッファ、aggregate cap によるスケーリングなどを実装。
- research モジュール（factor_research）の骨組みを追加
  - DuckDB 接続を受け取り momentum / value / volatility / liquidity 系のファクター算出を行う設計（未完の箇所あり）。
- ユーティリティ・インフラ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。stdout（StreamHandler）出力と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: psutil を用いたプロセス優先度設定ユーティリティを追加。Windows/Linux(macOS 等 POSIX) の差を吸収して優先度設定（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定の API を提供。権限不足等で失敗しても警告ログを出してスキップする堅牢性あり。
- 設定読み込み・検証
  - config.py: .env 自動ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml）。読み込みは OS 環境変数を保護する保護リストを使って行う。クォート文字や export 形式、インラインコメント等に対応した堅牢な .env 行パーサを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを導入し、環境変数経由の設定値アクセスを集約。多くのプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、paper_sqlite_path、pid_file_path、kill_flag_path、各種閾値、環境判定プロパティなど）を提供。PAPER_FILL_MODE と KABUSYS_ENV、LOG_LEVEL の検証ロジックを実装。
- 監視・実行に関する耐障害性強化
  - run_monitoring および run_execution で stop フラグ（data/stop_requested.flag）検出処理を実装し、外部から安全に停止できる仕組みを提供。
  - run_execution は execution.pid を利用して PID 書き込み / 管理を行う想定。ExecutionEngine がスレッドで実行され、stop フラグで安全に停止するループを採用。
- DB 初期化の補助
  - monitoring.monitoring_db.init_monitoring_db を呼び出して、必要な監視用テーブルの存在を冪等に保証する処理を各起動時に実行（monitoring と execution の双方で呼び出し）。

### Changed
- ログ出力方針
  - ログ出力は標準エラーではなく標準出力（stdout）へ出すように設計。これは cron / Task Scheduler 等でのリダイレクト運用を想定した仕様。
- ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。

### Fixed
- 環境変数読み込みの堅牢性向上
  - .env の行パースでクォート内のエスケープ処理や export プレフィックス、インラインコメントの扱いを改善し、不正な行を無視するようにした。
- ポーリング間隔取得の堅牢化
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合に警告を出し、デフォルト（60 秒）へフォールバックするようにした。これにより time.sleep に渡す値で例外が発生することを防止。
- プロセス優先度設定のフォールバック
  - 未対応 OS や権限不足で優先度設定ができない場合は警告ログを出して安全にスキップするように修正。

### Notes / その他
- Paper Trading と本番 DB は意図的に分離されている（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。paper_trading 実行時に誤って本番 DB を書き換えない設計。
- 一部モジュール（研究系の具体的な計算部分など）は実装の継続が想定されており、今後のリリースで詳細実装・最適化を行う予定。
- 設定ウィザード（config_setup）で生成される .env はセキュリティ上 Git にコミットしないことをドキュメント内に明記。

---

既知の注意点 / 移行手順:
- 自動 .env ロードが不要/好ましくない環境（CI 等）では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB に settings.sqlite_path（本番設定）を使用します。テスト環境で別 DB を使う場合は環境変数 SQLITE_PATH を適切に設定してください。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。無効な値は起動時に例外となります。

（以上）