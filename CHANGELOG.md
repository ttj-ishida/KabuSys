CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
---------

Added
- run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
  - 停止フラグ (data/stop_requested.flag) による安全な終了処理。
  - 監視は環境設定にかかわらず production 用の sqlite_path を使用して起動。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用（data/paper_trading.db デフォルト）し MockBrokerClient を利用可能。
  - 停止フラグ (data/stop_requested.flag) および pid ファイル管理（data/execution.pid）。
  - スレッドでエンジンを実行し、停止フラグで安全停止。
- config.py: 環境変数/設定管理を実装。
  - プロジェクトルートを .git または pyproject.toml から自動検出し .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを強化（export 形式、クォート文字列、インラインコメントの扱い、保護された OS 環境変数の尊重）。
  - 各種設定プロパティを提供（J-Quants, kabuAPI, DuckDB/SQLite パス, PID/Kill flag, 監視閾値, 環境判定メソッド等）。
  - Paper Trading 向けの PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH を追加。
- config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
  - J-Quants / kabu API / DB / ログ等の設定項目を対話で作成でき、.env に保存。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス・YAML ファイル存在チェック、live 環境時のガード等。
  - --strict モード（警告も失敗扱い）をサポート。
- utils/logging_setup.py: ログ設定ユーティリティを追加。
  - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーへ設定。
  - ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL の優先解決。
- utils/process_priority.py: プロセス優先度 / CPU affinity ユーティリティを追加。
  - Windows / POSIX を吸収し set_process_priority, set_cpu_affinity を提供。アクセス権限がない場合は警告を出してスキップ。
- portfolio/*: ポートフォリオ構築関連モジュールを追加（純粋関数群）。
  - portfolio_builder: 候補選出、等重・スコア重み配分。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数 calc_regime_multiplier。
  - position_sizing: 単元株丸め、リスクベース / 等配分の株数決定（aggregate cap / cost_buffer 対応）。
- tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、レイテンシ(P95含む)、リスク却下数などを集計し PASS/FAIL を判定。
  - コマンドライン引数 --from / --to / --db をサポート。
- research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム等、設計方針と定数定義を含む）。
- パッケージ初期化:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- DB/分析基盤:
  - DuckDB を分析用 DB として明示的に統合（duckdb 接続を各処理が受け取る設計）。
  - 監視・実行で DuckDB と SQLite の両方を使用する構成を採用。
- Logging:
  - ファイル出力とコンソール出力を統一的にセットアップする関数を全起動スクリプトから呼び出す仕様に変更。
- ExecutionEngine 起動フロー:
  - Execution スクリプトが起動時にプロセス優先度を "high" に設定するよう変更（set_process_priority）。
  - paper_trading 時は本番 DB から分離して専用 SQLite を使用するように明確化。

Fixed
- config._parse_env_line: クォート内のバックスラッシュエスケープやインラインコメントを正しく扱うよう改善（.env の堅牢性向上）。
- 設定ロード順序の明確化: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
- run_monitoring._get_poll_interval: 無効値（0 や負数、文字列等）を検知してデフォルトにフォールバックし、警告を出すよう改善。

Notes / Migration
- 環境変数の追加・変更:
  - 新たに利用される/推奨される環境変数:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用途）。
    - PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）。
    - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）。
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。
    - LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）。
    - KILL_FLAG_CLEAR_ON_START: 起動時の Kill Flag 自動クリア（'1' で有効。production では注意）。
  - 既存の .env を用いる場合は、config_setup.py で作成されるテンプレートと比較して不足項目を補完してください。
- ファイルフラグ:
  - 停止制御は data/stop_requested.flag、PID 管理は data/execution.pid（デフォルトパス）を使用します。運用環境で別パスを使う場合は環境変数 PID_FILE_PATH / KILL_FLAG_PATH を設定してください。
- 実行方法:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

[0.1.0] - 2026-04-18
--------------------
Added
- 初回公開 (v0.1.0) :
  - 自動売買システムのコアユーティリティ群を実装。
  - 起動スクリプト（監視・実行）、設定管理・ウィザード・検証ツール、ログ設定、プロセス優先度制御、ポートフォリオ構築ロジック、位置決めロジック、Paper Trading 検証ツール、ファクター計算の基本構成を含む。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Acknowledgements
----------------
- 本 CHANGELOG は、ソースコードの実装内容から推測して作成しています。実際のリリース履歴や日付はプロジェクトの方針に合わせて調整してください。