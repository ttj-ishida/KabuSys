CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。  
初回リリースの内容をコードベースから推測して記載しています。

0.1.0 — 2026-04-24
------------------

Added
- 基本アプリケーション骨組みを実装
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト / デーモン類
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 data/stop_requested.flag ファイルを検出して行う。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番用の sqlite_path を使用する設計。
    - SQLite および DuckDB への接続確立、監視用 DB の初期化処理を含む。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して MockBroker を利用する設計を明示。
    - 停止制御（stop flag）と PID ファイル管理のサポート。
    - ExecutionEngine を別スレッドで起動・監視し、停止フラグで安全に停止可能。

- 設定管理
  - Settings クラスを実装して環境変数 / .env の値をラップし提供。
    - J-Quants / kabuAPI / LINE 等の設定プロパティを提供。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）やログ関連（LOG_LEVEL）等の既定値を持つ。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）を実装。
    - KABUSYS_ENV の検証（development / paper_trading / live）と便利な is_live / is_paper / is_dev プロパティ。
  - 自動 .env ロード機能
    - プロジェクトルート検出（.git または pyproject.toml）に基づいて .env を自動読み込み。
    - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定時のみ）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パースは export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。

- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - 秘匿値のマスク表示、選択肢サポート、保存前の確認を実装。
    - 出力テンプレートに注意書き（.env を Git にコミットしない等）。
  - validate_config: 起動前に環境変数や config/*.yaml の存在・妥当性を検証する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML のパースチェック（PyYAML が存在する場合）。
    - `--strict` モードで警告を失敗扱いにできる。
    - live 環境向けの追加警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険性など）。

- ロギング / プロセス設定ユーティリティ
  - logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保存）を設定する共通ユーティリティを追加。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリア、ログフォーマット / 日付フォーマットを統一。
  - process_priority:
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - psutil を用い、Windows は priority class、POSIX は nice 値を設定。アクセス拒否等の例外は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数も提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 信号のソート（スコア降順、signal_rank でタイブレーク）、候補選定、等金額／スコア加重の重み計算を実装。
    - スコア全ゼロ時は等金額にフォールバックし WARNING を出す。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター露出に基づき候補を除外。unknown セクターは制限免除。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
  - portfolio.position_sizing
    - 発注株数計算（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下合計上限（max_utilization）、手数料/スリッページを考慮した cost_buffer、aggregate cap 時のスケーリングと端数配分ロジックを実装。

- Execution 関連（起案段階の構成）
  - Execution 側で BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager 等のコンポーネントを組み立て、実行する流れを実装（run_execution からの呼び出し）。
  - RiskManager に渡される既定パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値として broker.get_available_cash() を使用。

- Monitoring / Paper Trading ツール
  - monitoring_db 初期化呼び出し（監視テーブル確保）を run_monitoring/run_execution で保証。
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）、DB パスの指定（--db または env）をサポート。

- 研究用ファクター計算（着手）
  - research.factor_research の骨格を追加（モメンタム・MA200・ATR・出来高等の計算を想定）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して因子を計算する設計（関数の定義と定数が追加されているが一部実装は継続中）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / 補足
- .env の自動ロードはプロジェクトルートを検出して行うため、配布環境でも動作するように設計されています。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- run_monitoring は監視ログ・状態を本番用の sqlite_path に記録する仕様です（環境変数 KABUSYS_ENV に依存しません）。paper_trading の発注挙動のみ run_execution 側で paper_trading DB を用いて分離しています。
- ログは標準出力（stdout）へ出力され、ファイル出力は logs/<app_name>.log に日次でローテートされます。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続します。
- process_priority / cpu_affinity は可能な範囲でプラットフォーム依存の差分を吸収しますが、権限不足などで設定に失敗した場合は警告を出して処理を継続します。

今後の予定（推測）
- research.factor_research の残り実装（各ファクターの集計ロジック）を完了。
- ExecutionEngine や Broker クライアント周りの結合テスト、paper_trading / live の振る舞い検証。
- モニタリング・アラート（LINE 通知等）の具備と config/*.yaml を用いた設定反映。