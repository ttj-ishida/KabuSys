# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-23
初回リリース（コードベースから推測して記載）

### 追加（Added）
- 全体
  - パッケージ初期リリース。モジュール群をまとめたライブラリ「KabuSys」を提供。
  - バージョン情報: __version__ = "0.1.0"。

- 実行・監視ランナー
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite（デフォルト data/paper_trading.db）を使用して本番データと分離。
    - ブローカークライアントは BrokerClientFactory で生成（Mock / 実ブローカー切替を想定）。
    - Engine は別スレッドで起動し、 data/stop_requested.flag による停止処理と execution.pid による PID 管理をサポート。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知や KeyboardInterrupt 対応を実装。

- 設定関連
  - config.py：環境変数／.env 管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env/.env.local の自動ロード（OS 環境変数を保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、paper_trading 設定、監視閾値、環境フラグ等）をプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV/LOG_LEVEL の検証を実装。
  - config_setup.py：.env を対話式で作成・更新するウィザードを追加。
    - デフォルト値、選択肢、シークレット入力のサポート。
    - .env ファイルのテンプレート出力を実装。
  - validate_config.py：設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証等を実行。
    - --strict モードで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py：統一ログ設定ユーティリティを追加。
    - コンソール（stdout）用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイルハンドラをスキップ）と既存ハンドラの再設定を実装。
    - LOG_LEVEL / LOG_DIR / 引数による上書き対応。
  - utils/process_priority.py：プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）で差分を吸収し、nice 値や Windows 優先度へのマッピングを提供。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足等は警告でスキップ。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py：銘柄選定と重み計算関数を追加。
    - select_candidates（スコア降順・タイブレークルールを実装）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、スコア全0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py：
    - apply_sector_cap：セクター集中上限チェック。既存保有のセクター別時価から上限超過セクターを除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py：
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position / aggregate cap、コストバッファ考慮、available_cash に基づくスケールダウン（端数の再配分アルゴリズムあり）などを実装。

- 実行ログ／監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び出し、監視テーブルの存在を保証（冪等に作成）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py：
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - 判定基準（閾値）を定義して PASS/FAIL を判定する機能を提供。
    - 日付フィルタ（--from/--to）、--db オプションに対応。

- リサーチ
  - research/factor_research.py（骨格実装）
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルからモメンタム系、ボラティリティ、バリュー等のファクターを計算する設計を開始。モメンタム計算関数の定義を含む（実装途中のような箇所あり）。

### 変更（Changed）
- なし（初回リリースのため既存機能の変更履歴なし）。ただし内部デフォルト設定を多数導入：
  - デフォルトのポーリング間隔: 60 秒（MONITOR_POLL_INTERVAL で上書き可能）。
  - デフォルトログディレクトリ: logs/、ローテーション保持日数: 30 日。
  - デフォルト DB パス: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db、Paper Trading DB -> data/paper_trading.db。
  - Execution の RiskManager デフォルト設定（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20 等）を run_execution で使用。

### 修正（Fixed）
- なし（初回リリース）。実行時のエラーは try/except でログ出力・継続する設計が見られる（monitor の check_once() 呼び出し等）。

### 注意事項（その他）
- 環境変数管理:
  - 自動で .env/.env.local をロードする機能があるため、テスト環境や外部ツールでの .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する必要がある。
  - Settings._require は必須環境変数が未設定だと ValueError を投げるため、本番起動前に validate_config の実行や .env の事前準備を推奨。
- Paper Trading と Live のデータ分離:
  - paper_trading 環境では専用 SQLite を用いることで本番監視 DB と完全分離する設計が取られている。
- 実装の想定（将来的拡張や既知の TODO）:
  - position_sizing の lot_size を銘柄毎に柔軟化する拡張、price フォールバック処理（price が 0 の場合の対処）、research モジュールの未完部分の実装など。

もし特定の変更点（例: 追加したファイルや関数単位での差分）をより詳細に記載したい場合は、差分の対象となるコミットや変更時期の情報を教えてください。コードの追加・構成から推測した内容をベースに CHANGELOG を作成しています。