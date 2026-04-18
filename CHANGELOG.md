# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージ `kabusys` を追加（__version__ = 0.1.0）。
- 起動用スクリプトを追加:
  - run_execution.py — ExecutionEngine を起動するメインスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、発注データは分離された SQLite（デフォルト: data/paper_trading.db）に記録。
    - エンジンは別スレッドで実行され、data/stop_requested.flag による停止管理、実行 PID を data/execution.pid に記録する仕組みを持つ。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（data/monitoring.db デフォルト）を使用して監視テーブルを初期化・記録する仕様。
- 設定管理・ユーティリティを追加:
  - config.py
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と OS 環境変数保護（override と protected の扱い）。
    - .env 行のパーサは export prefix、クォート文字列、エスケープ、インラインコメントの扱いをサポート。
    - 多数のプロパティ（J-Quants、kabu API、DBパス、paper trading 特有設定、監視しきい値、環境種別チェックなど）を提供。
  - config_setup.py
    - 対話式の .env 作成ウィザードを実装。秘密値はマスク表示、既存値の再利用やデフォルトの提示が可能。
    - 書き込み時のテンプレートフォーマットを提供（.env に絶対コミットしない旨の注意付き）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI。--strict モードで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）などを実施。
- ポートフォリオ構築関連の純関数群（DB 参照なし）を追加:
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用（既存保有を参照して新規候補をフィルタ）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear 対応、未知はフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算、単元株丸め、per-position 上限・aggregate cap によるスケール調整、cost_buffer を考慮した保守的見積りを実装。
- 監視・実行コンポーネントの組立て（Execution 側）を追加:
  - ExecutionEngine の組み立て例（run_execution）: BrokerClientFactory によるブローカー生成、OrderRepository、OrderManager、RiskManager（デフォルト設定あり）、Reconciler を組み合わせてエンジンを起動。
  - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 関連、max_drawdown など）を提供し、初期ポートフォリオ値に broker.get_available_cash() を使用。
- 監視関連ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を起動前に呼び出して監視テーブルの存在を保証（冪等）。
  - SystemMonitor.check_once() をポーリングで繰り返す実装（run_monitoring）。
- ロギング / プロセス優先度ユーティリティを追加:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定。
    - ログレベル解決順、ログディレクトリ作成の失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を用いて Windows / POSIX (Linux, Darwin, FreeBSD) を吸収した優先度設定（high/normal/low）と CPU affinity 設定を提供。権限不足や未対応 OS では警告表示してスキップ。
- 研究用モジュール（duckdb を前提）:
  - research/factor_research.py（モメンタム等のファクター計算骨組み。prices_daily / raw_financials を参照する設計）。P95 等の統計ユーティリティあり（ファイル内で未完の箇所を含む可能性あり）。
- 運用ツール:
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを評価し PASS/FAIL を判定。
    - 各指標の閾値を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）し、データ欠損時には N/A 扱いでレポート化。
- パッケージエクスポート設定:
  - kabusys/portfolio/__init__.py で主要関数を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 重要な実行時挙動
- run_monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（デフォルト: data/monitoring.db）を使い監視データを記録します。監視用 DB を別にしたい場合は SQLITE_PATH を明示的に設定してください。
- run_execution は paper_trading モードで paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用するため、本番データと完全に分離してテスト可能です。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を指定可能。整数で 1 以上を期待し、不正値はデフォルト（60 秒）にフォールバックして警告を出力します。
- PAPER_FILL_MODE は paper trading の MockBrokerClient の約定挙動を制御します。有効値: instant / partial / never / reject。無効値は ValueError を送出します。
- .env 自動読み込みは既定で有効。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config の --strict を使うと警告も失敗扱い（exit 1）になります。本番 (KABUSYS_ENV=live) では追加の安全チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）が動作します。
- logging_setup は標準出力を stdout に出力するため、cron 等でのリダイレクト運用に適しています。ログファイルは LOG_DIR / <app_name>.log に日次ローテーションで保存されます（デフォルト logs/）。
- process_priority の設定は権限や OS によって失敗する場合があり、その場合は警告を出してスキップします。

---

開発者向け: 上記はコードから推測して作成した初期の変更履歴です。実際のリリースノートを作成する際は、コミットログやリリース日、影響範囲を確認して適宜追記・修正してください。