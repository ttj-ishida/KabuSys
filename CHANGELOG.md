# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

最新リリースは以下です。

[0.1.0] - 2026-04-20
-------------------

### Added
- 初期リリースを公開（パッケージバージョン: 0.1.0）。
- 実行用エントリスクリプトを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト。起動時にプロセス優先度を "high" に設定し、ExecutionEngine をスレッドで実行。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に完全分離して記録する（data/paper_trading.db）。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きに対応。監視は環境に関わらず本番 sqlite_path を使用（監視テーブルの初期化を行う）。
- 設定管理/ユーティリティ:
  - config.py — 環境変数/.env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）、Settings クラスによる型付きアクセスとバリデーションを提供。PAPER_FILL_MODE 等の値検証を実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py — 対話式 .env 作成ウィザード（キーの説明・既存値読み込み・マスク表示・保存機能）。
  - validate_config.py — 起動前チェック CLI。.env と config/*.yaml の存在や値を検証するツール（--strict オプションで警告を失敗扱いにできる）。
- ポートフォリオ構築関連（純粋関数群、DB参照なし）:
  - portfolio.portfolio_builder: 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。単元株丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer 考慮等を実装。
- ロギング・プロセス制御ユーティリティ:
  - utils.logging_setup: stdout ストリームハンドラと日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の優先解決、ディレクトリ作成失敗時のフォールバックをサポート。
  - utils.process_priority: Windows/POSIX の差分を吸収してプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity 設定を提供。アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ツール:
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。デフォルト DB パスや --from/--to/--db オプションに対応。
- research/factor_research: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity の計算方針と一部実装）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

### Changed
- run_execution.py と run_monitoring.py の起動フローにおいて、起動直後にプロセス優先度を設定するように統一（set_process_priority("high") を最初に実行）。
- run_execution.py で監視用テーブルの初期化（init_monitoring_db）を起動時に冪等に実行するようにして、監視関連テーブルの存在を保証。
- logging_setup: コンソール出力は stdout を使用するよう明確化（cron 等の stdout/err 統合運用を考慮）。

### Fixed
- 環境変数のパースと .env 読み込みにおいて、以下を改善:
  - config._parse_env_line: export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理を適切に処理。
  - _load_env_file: ファイルが開けない場合に warnings.warn で通知し処理継続するように改善。
- run_monitoring.py のポーリング間隔取得で不正値（0 以下や非整数）を検出した場合にデフォルト値にフォールバックし、警告ログを出すように変更（MONITOR_POLL_INTERVAL の堅牢化）。
- run_monitoring.py / run_execution.py で DB 接続（sqlite3, duckdb）を finally ブロックで確実にクローズするように修正。
- process_priority.set_process_priority / set_cpu_affinity: アクセス権限不足、未実装 API などの例外をキャッチして警告ログを出し、プロセスを停止させないように修正。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注記
- 監視プロセスは明示的に停止フラグファイル data/stop_requested.flag を監視し、検知時に安全に終了します。
- run_monitoring は監視データのために常に Settings.sqlite_path（本番想定のパス）を使用する点に注意してください（環境ごとの監視DB分離は現状行いません）。
- paper_trading 用 DB は Settings.paper_sqlite_path（デフォルト: data/paper_trading.db）で本番 DB と明確に分離されます。

変更やバグ修正の詳細が必要であれば、対象ファイル名・関数名を指定して問い合わせてください。