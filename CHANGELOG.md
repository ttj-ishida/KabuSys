# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）準拠で記載しています。

## [0.1.0] - 2026-04-19
初回リリース。KabuSys の基本的な起動スクリプト、環境設定、ロギング・プロセス管理ユーティリティ、ポートフォリオ構築ロジック、検証ツール群、および Paper Trading 向けレポート生成等を実装。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を設定し、SQLite / DuckDB に接続してエンジンをスレッドで実行する。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH による上書き可）。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による安全停止処理を実装。
    - 起動時に監視テーブルを冪等に初期化（init_monitoring_db 呼び出し）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境（KABUSYS_ENV）に関わらず本番の sqlite_path を参照する挙動を採用。
    - 停止フラグ検知・例外ハンドリング・接続クローズを実装。

- 環境設定・検証
  - config.py
    - Settings クラスを実装し、.env 自動読み込み（プロジェクトルートの検出は .git / pyproject.toml ベース）を行う。
    - .env パース機能強化（export プレフィックス、引用符付き値のエスケープ、インラインコメント処理等）。
    - 環境変数の必須チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）、env/log_level のバリデーション、paper_trading 用設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等）、監視閾値やパス設定を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。シークレット項目のマスク表示、既存 .env 読み込み、確認プロンプト、ファイル書き出しを提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が利用可能な場合）などを実装。
    - --strict オプションで警告を失敗として扱うモードを追加。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング初期化ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバックに対応。
    - ログレベル / ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - psutil を用いたプロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分吸収と権限不足時の安全なフォールバックを実装。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(n) を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアがすべて 0 の場合は等配分にフォールバックして警告をログ出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外するロジックを提供。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" をマッピング、未知レジームはフォールバックで 1.0 を返す）。

  - portfolio/position_sizing.py
    - 発注株数算出ロジック（calc_position_sizes）を実装。allocation_method="risk_based" / "equal" / "score" をサポートし、損切り率・リスク率・単元株（lot_size）丸め、単銘柄上限・集計上限（available_cash）によるスケーリング、手数料/スリッページを想定した cost_buffer を考慮するアルゴリズムを提供。
    - aggregate cap のスケーリング時に残差処理で lot_size 単位で追加配分するロジックを含む。

- Execution / Broker 組み立て関連（エントリポイントでの統合）
  - run_execution.py から呼び出すコンポーネント群（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）との連携インターフェースを整備（実装は別モジュールに分離）。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルを集計して稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、基準値に対する PASS/FAIL 判定を出力。
    - --from/--to/--db オプション、環境変数 PAPER_TRADING_SQLITE_PATH による DB パス指定をサポート。
    - P95 計算、欠損データへの安全なフォールバック、閾値定義を含む。

- 研究用モジュール（基盤実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計で、calc_momentum 等の関数を開始実装（計算範囲や定数を定義）。（実装は引き続き拡張を想定）

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- .env の自動読み込みは OS 環境変数を保護する仕組み（protected set）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供し、テストや CI の安全性を向上。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成しています。内部実装の詳細や別モジュール（例: ExecutionEngine 本体、BrokerClient 実装、SystemMonitor の詳細など）は別ファイルに依存しており、本稿は公開 API と CLI 挙動・設計意図を中心にまとめています。必要であれば、個別モジュール単位での変更履歴（より詳細な追加/修正項目）も作成できます。