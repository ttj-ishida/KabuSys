# Keep a Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

## Unreleased
（なし）

## [0.1.0] - 2026-04-18

### Added
- 初回リリース: KabuSys 自動売買フレームワークのコアモジュールを追加。
  - パッケージエントリポイントとバージョン
    - __version__ = "0.1.0"
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプト。
      - スレッドでエンジンを起動し、data/execution.pid への PID 管理、data/stop_requested.flag による停止制御を実装。
      - KABUSYS_ENV=paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderManager / OrderRepository / Reconciler / RiskManager といった依存コンポーネントの組み立て。
      - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）を提供。
    - run_monitoring.py
      - SystemMonitor ポーリングループを起動するスクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
      - 監視は環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用。
      - data/stop_requested.flag による停止検出。
  - 設定管理
    - config.py
      - .env 自動ロード (.env, .env.local)、OS 環境変数の保護（上書き制御）を実装。
      - .env の行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
      - Settings クラスを提供。主要プロパティ:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
        - KABUSYS_ENV（development / paper_trading / live、検証あり）
        - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト data/monitoring.db）
        - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
        - PAPER_FILL_MODE（instant|partial|never|reject の検証）
        - 各種監視閾値（CPU/MEM/DISK）、PID/KILL フラグパス、ログレベル等
    - config_setup.py
      - 対話式ウィザードで .env を初期作成/更新する CLI。
      - シークレット項目はマスク表示、Enter で既存値またはデフォルトを採用可能。
      - 生成される .env のテンプレートを提供（Git にコミットしないよう注意喚起のヘッダあり）。
  - 設定検証ツール
    - validate_config.py
      - .env と config/*.yaml の事前検証を行う CLI。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がインストールされている場合）を実施。
      - --strict オプションで警告をエラー扱いにできる。
      - 本番（KABUSYS_ENV=live）に関する追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告など）。
  - ポートフォリオ構築（純粋関数群、DB 非依存）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順＋タイブレークで選定。
      - calc_equal_weights: 等金額配分 (1/N)。
      - calc_score_weights: スコア加重配分（全スコア 0 の場合は等配分へフォールバックし WARNING）。
    - portfolio.risk_adjustment
      - apply_sector_cap: 既存ポジションに基づきセクター集中をチェックして候補をフィルタ（"unknown" セクターは除外しない）。
      - calc_regime_multiplier: market regimen に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を計算。
      - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap のスケールダウンロジックを実装。
      - risk_based モードでは risk_pct と stop_loss_pct から株数算出。
      - aggregate cap 超過時には再配分アルゴリズム（小数端数の優先付け）を実装。
  - 研究用（DuckDB ベースのファクター計算）
    - research.factor_research
      - Momentum / Value / Volatility / Liquidity 系ファクター設計を実装（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。
      - calc_momentum の骨子を追加（1M/3M/6M リターン、MA200 乖離、ウィンドウ不足時は None）。
      - （注）ファイル末尾に実装途上の箇所が存在（calc_momentum の続きが不完全）。
  - ツール
    - tools.paper_verification_report.py
      - Paper Trading 用の検証レポート生成 CLI。
      - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、API レイテンシ（avg/max/P95）。
      - P95 計算、しきい値を定義（稼働率 >=99.0%、fill>=90%、send>=95%、P95<=200 ms）。
      - 日付フィルタ (--from, --to) と DB パス指定 (--db) をサポート。環境変数 PAPER_TRADING_SQLITE_PATH 可。
  - ユーティリティ
    - utils.logging_setup
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次, 30日保持）を設定するユーティリティ。
      - ログレベル/ログディレクトリの解決順を明示。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority
      - Windows と POSIX(Linux/macOS/FreeBSD) を吸収するプロセス優先度設定（high/normal/low）を提供。
      - CPU affinity 設定ユーティリティ（最初 N コアに固定）を提供。
      - 権限不足や未対応 OS の場合は警告を出力してスキップ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

### Notes / Known issues
- research.factor_research の calc_momentum 実装がファイル末尾で中断している（実装途上）。使用する際は未完成箇所に注意してください。
- portfolio.risk_adjustment.apply_sector_cap 内で price が 0.0 の場合の扱いについて TODO コメントあり。価格データ欠損時にエクスポージャーが過少見積りされる可能性があるため、将来的なフォールバック（前日終値や取得原価）追加が示唆されています。
- position_sizing は現時点で全銘柄に共通の lot_size（デフォルト 100）を前提としている。将来的に銘柄別 lot_map への拡張予定あり（TODO コメント）。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する場合があり、その場合は警告でスキップする設計です。
- run_monitoring は監視 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用するため、開発環境で別 DB を期待する場合は設定を確認してください。

--- 

（必要に応じてバージョン別に詳細を分割できます。初回リリースのため機能一覧中心の記載としています。）