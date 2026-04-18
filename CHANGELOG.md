# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の規約に従って記載しています。

全般:
- 本ドキュメントはソースコードから推測して作成した変更履歴です。実際のコミット履歴に依存しないため、厳密な差分ではなく機能追加・振る舞いの要約を含みます。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初版を追加（kabusys v0.1.0）。
- 環境設定 / 起動周り
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数経由で各種設定を取得する仕組みを提供。
  - 自動 .env ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。読み込み順は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パース実装を独自に備え、export 形式・クォート・インラインコメント等を適切に扱う。
  - config_setup（src/kabusys/config_setup.py）: 対話式ウィザードで .env を生成/更新する CLI を追加。
  - validate_config（src/kabusys/validate_config.py）: .env と config/*.yaml の簡易検証を行う CLI を追加（--strict オプションで警告も失敗扱いに可能）。PyYAML 未インストール時は YAML 検証をスキップして警告を表示。
- 実行・監視プロセス
  - run_execution（src/kabusys/run_execution.py）: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用（本番 DB と分離）。
    - 実行中の停止制御に data/stop_requested.flag を利用。停止時は Engine.stop() を呼び出して終了。
    - 実行 PID を data/execution.pid に格納する仕組み（ExecutionEngine 側で利用想定）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring（src/kabusys/run_monitoring.py）: SystemMonitor のポーリング起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視 DB は本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 監視 DB 初期化
  - init_monitoring_db 呼び出し（監視テーブルの冪等な初期化）を、実行・監視起動スクリプトに追加。
- ロギング
  - setup_logging（src/kabusys/utils/logging_setup.py）を導入。全起動スクリプトから統一的に利用可能。
    - stdout へ StreamHandler（標準出力）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name 引数で設定上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout だけで動作。
- プロセス優先度 / CPU 固定
  - set_process_priority / set_cpu_affinity（src/kabusys/utils/process_priority.py）を追加。Windows/Linux (POSIX) の差分を吸収し、権限不足等は警告にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.builder（select_candidates, calc_equal_weights, calc_score_weights）
  - portfolio.risk_adjustment（apply_sector_cap, calc_regime_multiplier）
    - レジーム別の乗数（bull=1.0, neutral=0.7, bear=0.3）と未知レジームでのフォールバック動作を実装。
  - portfolio.position_sizing（calc_position_sizes）
    - risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮した保守的な見積りとスケールダウンロジックを実装。
- Execution 周りの骨格
  - 実行エンジンの組み立て例として OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み合わせを run_execution で定義（実装ファイルは別モジュールに存在する想定）。
  - RiskManager のデフォルト設定（max_position_pct 等）と初期ポートフォリオ値に broker.get_available_cash() を利用する構成を用意。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、閾値（稼働率 >=99% 等）に基づく PASS/FAIL レポートを出力。
    - P95 計算、期間フィルタ（--from / --to）、DB 存在チェック、テーブル欠損時のフォールバックを実装。
- 研究用ファクター計算（開始）
  - research/factor_research.py を追加（Momentum 等のファクター計算を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を明記（実装は継続中）。

### Changed
- ログ出力ポリシー:
  - StreamHandler を stdout に固定（cron / Task Scheduler 等で stdout/stderr のリダイレクトが安定するため）。既存の stderr 出力との差異に注意。
- .env 読み込み挙動:
  - .env.local は .env の上書きとして読み込まれるようにした（OS 環境変数は上書きされないよう保護）。
- モニタリングの DB 接続:
  - run_monitoring は実行環境にかかわらず settings.sqlite_path（本番監視 DB）を使用する仕様に明確化。

### Fixed
- 環境変数パースの改善:
  - export 前置、シングル/ダブルクォートのエスケープ処理、コメント判定の取り扱いを強化し、不正な .env 行を無視することで堅牢性を向上。
- Process priority / affinity の安全な失敗ハンドリング:
  - 権限不足や未サポートプラットフォームでの例外をキャッチして警告にフォールバックするように修正。

### Notes / Behavioral details
- MONITOR_POLL_INTERVAL は整数で 1 以上を期待。0 以下や非数が指定された場合はデフォルト 60 秒にフォールバックし警告を出力する。
- run_execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する想定。
- apply_sector_cap は "unknown" セクターを除外対象にしない（上限適用除外）。
- calc_score_weights は全銘柄のスコア合計が 0 の場合に等配分へフォールバックして警告ログを出す。
- ログディレクトリ作成に失敗した場合はログファイル出力を諦めてもアプリは続行する（コンソールログのみ）。

---

将来的に細分化されたバージョンや実装の追加・修正がある場合は、各モジュール単位で詳細なリリースノートを追加してください。必要であれば、この CHANGELOG をベースに、個別の機能変更点をさらに掘り下げて記載します。