# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在バージョン: 0.1.0

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-24

初回リリース。本リポジトリに含まれる主要機能・ユーティリティを追加。

### Added

- 基本パッケージ情報
  - kabusys パッケージ初期バージョンを追加（__version__ = 0.1.0）。

- 実行用スクリプト / デーモン化関連
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用した安全停止処理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。デフォルト 60 秒。
    - 監視 DB は環境にかかわらず本番用 sqlite_path を使用（監視は本番 DB 参照を前提）。
    - 停止フラグの検出と例外ハンドリングを実装。

- 設定管理 / ユーティリティ
  - config.py
    - 環境変数と .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env の自動ロードは OS 環境変数を保護（既存の OS 環境変数を上書きしない）し、.env.local による上書きをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応など堅牢に実装。
    - Settings クラスを提供。主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（値検証あり）
      - PID/KILL フラグパス、閾値（CPU/MEM/DISK）、ログレベル、環境判定（is_live/is_paper/is_dev）など。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - 入力補助、シークレット値のマスク、デフォルト・選択肢サポート、保存前の確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在／パース（PyYAML があれば実行）などを実施。
    - --strict オプションで警告を失敗扱いにできる。
    - KABUSYS_ENV=live の場合に追加のガード（LINE 設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定）を警告。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - コンソール出力（stdout）用 StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log、30日保持）。
    - 既存ハンドラをクリアして重複を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで続行。
    - 環境変数 LOG_LEVEL / LOG_DIR に対応。引数で上書き可能。
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）設定および CPU affinity 固定ユーティリティを追加。
    - Windows / POSIX の差分を吸収し、安全にフォールバック（権限不足などは警告でスキップ）。
    - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア合計が0のときは等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別集中上限を適用（既存保有の時価を基に除外）、売却予定銘柄の除外対応、"unknown" セクターは上限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 等）を提供。未知レジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき各銘柄の発注株数を決定。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - cost_buffer を考慮した保守的コスト見積り、aggregate cap によるスケーリングロジック（残差処理で再配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計して検証レポートを生成する CLI。
    - 指標:
      - 稼働率（uptime_pct）、注文成立率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - デフォルト基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づき PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加。モメンタム（1M/3M/6M、MA200 乖離）、ATR/出来高などの計算を行う設計。
    - DuckDB 経由で prices_daily / raw_financials を参照する想定の API を用意（calc_momentum 等の関数を含む）。

- DB 初期化ユーティリティ
  - monitoring/monitoring_db.py（参照・初期化関数を run_* スクリプトが呼び出すことで監視テーブルの存在を保証／冪等に初期化可能）

### Changed

- 環境変数の読み込みポリシー
  - OS 環境変数を優先する自動ロード方式を採用（.env は OS 変数が未定義時のみ適用、.env.local による上書きを許可）。テスト等のために KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化できる。

- ログ出力
  - コンソールは stderr ではなく stdout を使用（cron / Task Scheduler で stdout/stderr をまとめて扱う環境を考慮）。

### Fixed

- （初版のため既知の軽微な問題はリファクタリング段階で追って対応予定。現時点で重大なバグフィックスは無し。）

### Notes / Migration

- 監視（run_monitoring）は監視用の SQLite DB として Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。環境（development / paper_trading / live）に依存せず本番用の sqlite_path を参照する実装になっている点に注意してください。
- Paper Trading を完全に分離して運用する場合は環境変数 PAPER_TRADING_SQLITE_PATH を設定してください（run_execution は paper_trading 環境で専用 DB を使用します）。
- 設定ファイル（.env）を Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

以上。詳細は各モジュールの docstring / CLI ヘルプを参照してください。