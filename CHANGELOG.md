CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に従い、セマンティックバージョニングを採用しています。
各リリースには重要な変更点（追加・変更・修正など）を日本語で記載しています。

なお、本リポジトリはまだ初回リリース相当の内容のため、以下はバージョン 0.1.0 のリリースノートです。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎モジュールを追加。
  - 実行/監視ランナー
    - run_execution.py: ExecutionEngine 起動用スクリプト（thread ベースのセッション実行、停止フラグ監視、paper_trading 用 DB 分離、BrokerClientFactory 経由でブローカークライアントを生成）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ監視）。
  - 環境/設定管理
    - config.py: Settings クラスで環境変数からアプリ設定を取得。自動 .env 読み込み機能（.env, .env.local）と保護機能を実装。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - validate_config.py: .env と config/*.yaml の事前検証用 CLI。--strict オプションで警告を失敗扱いに可能。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
    - portfolio.portfolio_builder: 銘柄選定 (select_candidates)、等重・スコア重み計算 (calc_equal_weights / calc_score_weights) を実装。
    - portfolio.position_sizing: 各銘柄の発注株数決定ロジック（risk_based / equal / score、単元株丸め、aggregate cap スケーリング等）。
    - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
    - portfolio.__init__: 主要 API をエクスポート。
  - リサーチ/ファクター計算
    - research.factor_research: DuckDB を用いたモメンタム／ボラティリティ等のファクター計算ユーティリティ（prices_daily / raw_financials 参照）。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト（稼働率、注文成功率、レイテンシ統計、PASS/FAIL 判定）。
  - ユーティリティ
    - utils.process_priority: プロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 設定ユーティリティ。プラットフォーム差分を吸収し、権限不足時は警告でスキップ。

Changed
- デフォルト設定・動作
  - Settings: KABUSYS_ENV の既定値は "development"、ログレベル既定は "INFO"。データベースのデフォルトパスは DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db。
  - run_monitoring は KABUSYS_ENV に依存せず「本番用」sqlite_path を使用する仕様（監視データは本番 DB に蓄積する想定）。
  - run_execution は paper_trading 実行時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
  - ランナー起動時にプロセス優先度を "high" に設定する挙動を追加（set_process_priority("high") を呼び出し）。権限がない環境では警告を出してスキップ。
  - 停止制御はプロジェクト内の data/stop_requested.flag（および execution 用の execution.pid）を用いる統一的なフラグ方式を採用。

Fixed
- .env 読み込みの堅牢化（config.py）
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応したパーサを実装。
  - 自動読み込み順序を OS 環境変数 > .env.local > .env とし、既存の OS 環境変数を保護（上書き保護）するロジックを導入。
  - .env 読み込み失敗時に警告を発するように改良。
- validate_config.py
  - .yaml ファイル検証（PyYAML が導入されている場合）や各種環境変数の存在チェック、パスの親ディレクトリ存在チェック、KABUSYS_ENV=live に対する追加警告等を実装。
- position_sizing / risk_adjustment
  - 各種端数処理・上限チェック・コストバッファの考慮など、発注量算出ロジックの細部を実装し安全弁（aggregate cap のスケーリング、lot 単位増分の再配分）を備えた。

Security
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で未設定時に例外を発生させるようにしており、起動前に validate_config で検出可能。
- .env の注意喚起を config_setup のヘッダに明記（.env をコミットしないこと）。

Notes
- 実行方法の例
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の主要項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development | paper_trading | live）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒数、run_monitoring で使用）
  - KILL_FLAG_CLEAR_ON_START（production 防護のためデフォルト 0 推奨）
- DuckDB/SQLite の利用
  - 各種分析・ファクター計算は DuckDB（DUCKDB_PATH）を利用。監視・注文ログは SQLite（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）に格納。
- ロギング
  - 各ランナーは logging.basicConfig(level=logging.INFO) を使用。LOG_LEVEL 環境変数で変更可能。

Deprecated
- なし

Removed
- なし

Contributing
- バグ報告、改善提案、機能追加は Issue を立ててください。リポジトリには .env を含めないでください。

ライセンス
- リポジトリ内の LICENSE を確認してください（ここでは省略）。