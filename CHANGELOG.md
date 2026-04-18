CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリースを公開。
- 実行用スクリプト:
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を介して完全に本番 DB から分離して実行可能。
    - エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag を監視して安全に停止可能。起動時の PID 管理用に data/execution.pid を利用。
    - ExecutionEngine の構築時に OrderRepository、OrderManager、RiskManager（デフォルト設定含む）、Reconciler を組み立てる。RiskManager の初期ポートフォリオ値は broker.get_available_cash() を参照して設定される。
- 監視用スクリプト:
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視モジュールは環境に関わらず本番用の sqlite_path を使用する旨の挙動を明示。
    - 停止はプロジェクトルート/data/stop_requested.flag の存在で検出。
- 設定管理:
  - config.py を追加。.env 自動読み込み（.env → .env.local、OS 環境変数の保護）、環境変数パース、Settings クラスによるプロパティアクセスを提供。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
    - 環境変数の必須チェック（_require）や各種パス・閾値のデフォルト解決を実装。
- 設定ユーティリティ:
  - config_setup.py を追加。対話式ウィザードで .env を生成・更新する機能を提供（シークレットマスク・選択肢・デフォルト値表示など）。
  - validate_config.py を追加。起動前に .env および config/*.yaml の設定検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML 有無に応じてスキップ）や本番環境向けの追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築:
  - portfolio モジュールを追加（portfolio_builder、position_sizing、risk_adjustment）。
    - 銘柄候補選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights、calc_score_weights）。
    - セクター集中制限の適用（apply_sector_cap）: 既存保有を基にセクター暴露を計算し上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear のマッピングを実装（未知レジームはフォールバックで 1.0）。
    - 株数決定ロジック（calc_position_sizes）: risk_based / equal / score の配分方式に対応し、単元株（lot_size）丸め、1 銘柄上限や aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
- ログ / プロセスユーティリティ:
  - utils.logging_setup を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。既存ハンドラの重複防止やログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を考慮。
  - utils.process_priority を追加。Windows/Linux/macOS を抽象化してプロセス優先度（high/normal/low）を設定するユーティリティを実装。CPU affinity 設定関数（set_cpu_affinity）も提供。権限不足や未対応 OS では警告を出してスキップする堅牢性を確保。
- 監視 DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプト（execution/monitoring）から呼び出して監視テーブルの存在を保証（冪等）。
- ツール:
  - tools.paper_verification_report.py を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を参照して検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し閾値比較して PASS/FAIL を判定（デフォルト閾値をコード内に定義）。
    - 日付フィルタ、DB 存在チェック、NULL/データ不足時の扱いを実装。
- 研究用:
  - research.factor_research を追加（モメンタム等ファクター計算用の骨組みと定数実装。DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
- パッケージ情報:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのためなし）

Fixed
- ログ設定時に既存ハンドラを flush/close してから削除することで二重出力等の問題を回避。
- 起動時に監視テーブルが存在しないときのエラーに対し、init_monitoring_db を呼んで冪等に対応。

Removed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Security
- （該当なし）

Notes
- .env ファイルは機密情報を含むためコミットしない旨を config_setup.py の出力ヘッダに明記。
- 本番環境（KABUSYS_ENV=live）では Kill Switch 等の設定に注意するため validate_config で警告を出すガードを設けています。