CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。日付や実装はソースコードの内容から推測して記載しています。

Unreleased
----------
- なし

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース。KabuSys の基本機能群を実装。
- アプリケーションバージョンを設定: __version__ = "0.1.0"。
- 環境設定 / ロード
  - Settings クラスによる環境変数管理を実装（config.py）。
  - .env 自動ロード機能を実装（プロジェクトルートの .env, .env.local を読み込み、OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env ファイルの柔軟なパースを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応）。
  - 環境変数必須チェック用の _require ユーティリティを追加。
  - Settings による各種設定プロパティを実装（DB パス、PID/Kill flag パス、閾値、ログレベル、環境判定、paper_trading 用パラメータなど）。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。

- CLI / ユーティリティ
  - 環境設定ウィザード: python -m kabusys.config_setup（対話式に .env を作成・更新）（config_setup.py）。
  - 設定検証 CLI: python -m kabusys.validate_config（.env と config/*.yaml の事前検査。--strict オプションで警告を fail 扱いにする）（validate_config.py）。
  - Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report（tools/paper_verification_report.py）。
    - レポートはシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定。
    - コマンドラインで --from/--to/--db オプションをサポート。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 判定基準（例）: 稼働率 >= 99%、注文成立率 >= 90%、送信率 >= 95%、P95 <= 200ms。

- 実行 / 監視プロセス起動スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - プロセス優先度を high に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てて実行。
    - ExecutionEngine は別スレッドで run_session を実行し、data/stop_requested.flag による停止検知を行う。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。
  - 監視ループ起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を統一）。
    - SystemMonitor(check_once を呼ぶ) を定期実行し、停止フラグで終了。
    - duckdb との接続を行い、分析用 DB を利用。

- 監視 DB 初期化
  - init_monitoring_db(sqlite_conn) により監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築 / リスク管理の純粋関数群（DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選出。
    - calc_equal_weights / calc_score_weights: 等分配、スコア加重配分を計算（スコア全体が 0 の場合に等分配へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を適用（売却予定コードの除外などに対応）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に従って発注株数を算出。lot_size（単元）丸め、max_position_pct、max_utilization、コストバッファ、aggregate cap に基づくスケーリングロジックを実装。

- 研究用ファクター計算（research.factor_research）
  - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を DuckDB の prices_daily を用いて計算。
  - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率などを計算するためのクエリ骨格を実装（データ不足時の None 処理を含む）。
  - DuckDB を利用したオンメモリ分析を前提。

- ユーティリティ
  - utils.process_priority に set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）で適切に優先度（nice / HIGH_PRIORITY_CLASS）を設定。psutil の例外をハンドリングしてフォールバック。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定）。利用不可時は警告を出してスキップ。

Changed
- リポジトリ構成を整備し、モジュール単位での責務を明確化（config, execution, monitoring, portfolio, research, tools, utils）。
- .env マネージャの読み込み優先度を OS 環境変数 > .env.local > .env に明確化。OS 環境変数は protected として .env で上書きされない。

Fixed
- 環境変数読み込みの堅牢化:
  - 不正な MONITOR_POLL_INTERVAL（0 以下や非整数値）を検出してデフォルトにフォールバックし、警告ログを出力するようにした。
  - .env のパースにおけるクォート／エスケープ／コメント処理を改善し、より一般的な .env 記述に対応。
- 実行中の例外ハンドリング:
  - 監視ループ内で monitor.check_once() が例外を投げてもループを継続し、例外内容をログ出力するようにした（監視の堅牢化）。
  - process priority / cpu affinity 設定で権限やプラットフォーム非対応の例外を捕捉し、エラーで落とさず警告にとどめるようにした。

Security
- .env 書き込み時に注意を促すヘッダーコメントを追加（config_setup にて .env を生成する際に Git にコミットしない旨を明記）。

Known issues / Notes
- portfolio.position_sizing 内で price が 0 や欠損のときにエクスポージャーや発注量が過少に見積もられる可能性がある（TODO コメントあり）。将来的に前日終値や取得原価をフォールバックする拡張が想定されている。
- research.calc_volatility など一部の関数は大規模な DuckDB クエリを実行するため、入力テーブルのスキーマ（prices_daily 等）やデータ品質に依存する。必要に応じて前処理/NULL ハンドリングを見直すこと。
- validate_config の YAML パースは PyYAML が未インストールの場合スキップされる。CI 等では PyYAML をインストールすることを推奨。

References / Usage hints
- 起動:
  - 監視: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL=... でポーリング間隔を調整可能（デフォルト 60 秒）。
    - 監視は常に settings.sqlite_path（本番監視 DB）を使用。
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（settings.paper_sqlite_path）と MockBrokerClient を使用。
- 設定:
  - python -m kabusys.config_setup で .env を作成後、python -m kabusys.validate_config で事前検証することを推奨。
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可能。

（以上）