Keep a Changelog
=================

すべての注目すべき変更を記録します。このファイルは Keep a Changelog の形式に準拠しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

フォーマット
-----------
- Unreleased: 現在開発中の変更
- 各リリースは「Added / Changed / Fixed / Removed / Deprecated / Security」で分類

Unreleased
----------
- 現在ありません。

[0.1.0] - 2026-04-20
--------------------

Added
- 全体
  - 初期公開リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止監視（stop フラグファイル経由）を実装。
    - 実行中は PID ファイル（data/execution.pid）を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用する設計。
    - 停止はプロジェクトルートの data/stop_requested.flag を監視。

- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を探して .env/.env.local を自動読込（自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - 独自の .env パーサ実装（コメント、クォート、export 形式対応）。
    - Settings クラスを提供し、アプリ設定（API トークン、DB パス、各閾値、環境判定等）をプロパティ経由で取得。validation（有効値チェック）を含む。
    - paper_trading 用の設定 PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などをサポート。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - J-Quants / kabu API / DB / ログレベル / Kill Switch 設定などを対話的に入力・保存可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認（PyYAML がない場合は警告を出してスキップ）、本番用ガードチェック等。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 引数 / 環境変数（LOG_LEVEL / LOG_DIR）で挙動を制御。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。
    - Windows / POSIX を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) で CPU affinity を設定（オプション）。
    - 権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・タイブレーク考慮で選定。
    - calc_equal_weights, calc_score_weights: 等金額・スコア重みの計算。スコア全0 時は等金額にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャが閾値を超える場合に新規候補を除外する機能（unknown セクターは免除）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を計算。
    - 単元株（lot_size）に丸め、per-position と aggregate の上限を考慮、available_cash を超えた場合はスケールダウンして残差配分を行う実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的な見積。

- 研究・分析
  - research/factor_research.py:
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）用の雛形を追加。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を記述。
    - モメンタム計算関数 calc_momentum の実装を開始（注: ファイル末尾で切れているため未完）。
  - DuckDB（duckdb）をデフォルトの分析 DB として利用。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード検証レポート生成スクリプトを追加。
    - 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）などを算出・判定。
    - 閾値定義（P95 <= 200 ms など）と PASS/FAIL 判定ロジックを実装。
    - --from/--to/--db オプションにより期間・DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を参照。

- 監視（Monitoring）
  - monitoring_db.init_monitoring_db の呼び出しで監視テーブルを起動時に整備（冪等）。
  - SystemMonitor を利用して単一チェック check_once を行う設計（run_monitoring でポーリングループを実行）。

Changed
- （該当なし — 初期リリース）

Fixed
- （該当なし — 初期リリース）

Removed
- （該当なし）

Deprecated
- （該当なし）

Security
- （該当なし）

Notes / Known issues / TODOs
- config._load_env_file の自動読み込みはプロジェクトルート検出に依存するため、一部の配布状況では自動読込をスキップする（意図的な設計）。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャが過少見積りされる可能性があるという TODO コメントが存在。将来的に前日終値等のフォールバックを検討する必要あり。
- research/factor_research.py はファイル末尾で途中（calc_momentum の続きが欠けている）ため、完全実装は未完。
- 一部の機能（ブローカークライアントの具象実装、ExecutionEngine の内部実装、SystemMonitor の具体処理等）はこの差分に含まれた呼び出し側のみで、実装詳細は別モジュールに依存。

参考（主な環境変数 / デフォルト）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- LOG_LEVEL: default INFO
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default 60）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill フラグ自動クリア（0 推奨）

今後の予定（提案）
- research モジュールの完成（全ファクター実装・テスト）
- price 欠損時のフォールバックロジック実装（セクター露出計算の精度向上）
- 設定バリデーション強化や unit tests の追加
- CLI の詳細ドキュメントとデプロイ手順の整備

----