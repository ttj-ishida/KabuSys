CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このファイルはリポジトリのコードから推測された機能・改善点を元に作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased: 次回リリースに向けた未リリース項目（現状なし）
- 各バージョンには日付を付与

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-24
-------------------

Added
- 基本パッケージ初期実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（MockBrokerClient によるペーパートレード運用を想定）。
    - Engine の実行はデーモンスレッドで行い、data/stop_requested.flag による停止を監視。実行中は execution.pid（data/execution.pid）を使用。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors など）を設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバック。
    - 監視は環境に依らず本番用 sqlite_path を使用。
    - 停止は data/stop_requested.flag による検知。KeyboardInterrupt のハンドリングあり。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順制御（OS 環境変数は保護、.env.local は上書き可能）。
    - .env 行パーサ (_parse_env_line) を実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, kill_flag_clear_on_start, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL など）。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を追加。
    - シークレット値はマスク表示、選択肢・デフォルト表示、キャンセル時の扱い等を実装。
    - .env の書き込み時にヘッダコメントを付与し「.env を Git にコミットしない」旨を明記。
- 設定検証
  - validate_config.py
    - .env および config/*.yaml の起動前チェック CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パースチェック（PyYAML がインストールされていない場合は警告）を実装。
    - --strict モードで警告も失敗扱いにできる。
    - 本番 (KABUSYS_ENV=live) 向けのガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を追加。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル、ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソール出力のみで継続するフォールバック処理を実装。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows と POSIX の差分を吸収して優先度（nice / Windows priority class）を設定。
    - set_cpu_affinity(cpu_count) を追加。最初の N コアにプロセスをピン留めするユーティリティを提供。
    - 権限不足や未対応 OS に対する警告ハンドリングを実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(buy_signals, max_positions) を追加（スコア降順・タイブレークに signal_rank を使用）。
    - calc_equal_weights, calc_score_weights を追加（score 全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限チェックにより候補を除外する機能を実装（sell_codes を除外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み／候補／リスクベースに応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash 超過時のスケーリングと残差処理）を実装。
    - allocation_method は "risk_based"/"equal"/"score" をサポート。cost_buffer による保守的見積りを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計し、検証レポートを生成する CLI を追加。
    - 期間フィルタ（--from/--to）、--db オプションをサポート。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等を算出。
    - Pass/Fail 基準値を設定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）。
    - レポートは標準出力に整ったフォーマットで出力。
- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity などのファクター計算用ユーティリティ（DuckDB 接続を使用）を実装する設計と一部定義を追加。（ファイルは途中まで実装）

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Deprecated
- なし

Removed
- なし

Security
- .env の取り扱いに関する注意を明記（config_setup にて .env を Git にコミットしない旨を出力）。
- 必須トークン類（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で必須扱いとし、未設定時に明確なエラーメッセージを出すように実装。

注意事項 / マイグレーション
- PAPER_TRADING 環境:
  - paper_trading 用の SQLite を使用するため、運用中に本番 DB に誤って書き込まれるリスクは低減されています。paper_trading を使用する場合は PAPER_TRADING_SQLITE_PATH を確認してください。
- .env 自動ロード:
  - ランタイム環境での自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストや CI で利用）。
- ログ:
  - デフォルトで logs/ にログファイルを出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度:
  - set_process_priority は OS の権限やプラットフォームによって失敗する場合があり、その際は警告ログが出力されます（処理は継続します）。

関連コマンド（例）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行／監視スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

---
注記: 本 CHANGELOG は提示されたソースコードから機能・意図を推測して作成したものであり、実際のコミット履歴や追加のファイル（例えば tests, docs, CI 設定など）は反映していません。必要であれば、より詳細な差分（個別コミットメッセージや変更ファイル一覧）を元に追記・修正します。