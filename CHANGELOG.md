CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本機能の初期実装を追加（初回公開）。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
- 実行スクリプト:
  - run_execution.py を追加。ExecutionEngine の起動フローを実装。
    - 環境に応じて paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading では MockBrokerClient を使用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知時に安全に停止するロジックを実装。
    - PID ファイルサポート（data/execution.pid）。
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を採用。
    - 停止フラグ（data/stop_requested.flag）検知・例外ハンドリング・Graceful shutdown を実装。
- 環境設定 / 設定検証:
  - config.py を追加。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env と .env.local の読み込み順序、OS 環境変数保護（上書き抑制）を含む読み込みロジックを実装。
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 各種閾値 / 環境 (development/paper_trading/live) 判定等のプロパティを公開。PAPER_FILL_MODE の検証等も含む。
  - config_setup.py を追加。対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目のマスク表示、選択肢・デフォルトの提示、保存前の確認を実装。
  - validate_config.py を追加。起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検査（PyYAML 未導入時は警告）、本番向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告をエラー扱いに可能。
- ロギング / プロセス制御ユーティリティ:
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定する統一関数 setup_logging を提供。
    - LOG_LEVEL / LOG_DIR の環境変数と関数引数による解決、ディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py を追加。
    - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度（High/Normal/Low）を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) で CPU affinity の固定をサポート（実行環境に依存し、失敗時は警告でスキップ）。
- ポートフォリオ構築（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py を追加。
    - select_candidates（スコア降順で上位 N 抽出）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py を追加。
    - apply_sector_cap（セクター別集中上限を超える場合の候補除外）、calc_regime_multiplier（market regime に応じた投下資金乗数）を実装。未知レジーム時のフォールバックとログ出力を含む。
  - portfolio/position_sizing.py を追加。
    - calc_position_sizes を実装。allocation_method（"risk_based", "equal", "score"）に対応し、lot_size に基づく丸め、per-stock 上限・aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮した保守的見積り、残差配分ロジックなどを実装。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py を追加。
    - paper_trading の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下件数、API レイテンシ（avg, max, P95）を集計してレポートを生成。
    - P95 の計算、日付フィルタ（--from / --to）、しきい値による PASS/FAIL 判定を実装（デフォルト閾値をソース内で定義）。
- research/factor_research.py を追加（ファクター計算基盤）。
  - Momentum / Value / Volatility / Liquidity の計算方針を実装方針として定義し、DuckDB を使った prices_daily / raw_financials 参照の設計を開始。モメンタム計算のための定数や calc_momentum の骨格を含む（今後の拡張を想定）。
- 監視 DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプト内で呼び出し、監視テーブルの存在を冪等的に保証。

Changed
- なし（初回リリースのため変更履歴は追加のみ）。

Fixed
- なし（初回リリース）。

Security
- なし

Notes / Usage highlights
- 自動 .env ロードはデフォルトで有効。テストや CI で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution の paper_trading モードは本番 DB と完全に分離された専用 DB（PAPER_TRADING_SQLITE_PATH）を使用するようになっています。実運用時は KABUSYS_ENV を適切に設定してください（live を指定すると本番動作になります）。
- ロギングはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。必要に応じて LOG_DIR 環境変数または setup_logging の引数で上書きしてください。
- MONITOR_POLL_INTERVAL に無効な値を設定した場合はログに警告を出し、デフォルトの 60 秒にフォールバックします。
- calc_position_sizes は lot_size（単元）単位で丸め、利用可能現金（available_cash）を超えた場合はスケールダウンして残差は大きい順に単元を追加配分するアルゴリズムを実装しています。

今後の予定（短期）
- factor_research の完全実装（Momentum の SQL 実装や他ファクター）。
- ExecutionEngine / BrokerClient の詳細なユニットテストと Mock の整備。
- 監視（SystemMonitor）・実行（ExecutionEngine）の e2e テストスイート整備。
- config/*.yaml のテンプレート生成スクリプトやサンプルデータの追加。

Refer to source files for details:
- src/kabusys/config.py, config_setup.py, validate_config.py
- src/kabusys/run_execution.py, run_monitoring.py
- src/kabusys/utils/logging_setup.py, process_priority.py
- src/kabusys/portfolio/*
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py