# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの内容から推測して作成しています。

全体指針:
- Unreleased: 今後の未リリースの変更を記載するためのプレースホルダ
- 各リリースは 日付 (YYYY-MM-DD) を付記

## [Unreleased]
- ドキュメントや小さな改善、内部実装の調整など（将来追記）

## [0.1.0] - 2026-04-18
初回リリース。システムの起動スクリプト、設定管理、監視、実行、ポートフォリオ構築、ユーティリティ、検証ツール群を含む。

### Added
- 基本アプリケーション情報
  - パッケージメタ情報にバージョンを追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - 監視は環境（KABUSYS_ENV）に関係なく本番用の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離。
    - 停止フラグと PID ファイル（data/execution.pid）を扱い、安全にスレッドを停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: 環境変数/.env の自動読み込み機能を追加（.env / .env.local の優先順位、OS 環境変数の保護）。
    - .env の自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パース機能を実装（コメント、export プレフィックス、クォート・エスケープ対応）。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、DB パス、ログレベル、各種閾値、環境判定用プロパティ等）を公開。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
  - config_setup.py: 対話型ウィザードで .env を初期作成/更新する CLI を追加。
    - 秘匿入力（トークン等）や選択肢、デフォルト、既存値の再利用に対応。
    - .env の書式化保存を実装（ファイル内コメント含む）。

- 設定検証ツール
  - validate_config.py: .env および config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- モニタリング関連
  - monitoring の初期化ヘルパー（init_monitoring_db を利用）を起動スクリプトから呼び出すことで監視用テーブルの存在を保証。

- 実行（Execution）関連
  - BrokerClientFactory 経由でブローカークライアントを生成。paper_trading と live を分離。
  - ExecutionEngine の起動/停止フロー、OrderRepository/OrderManager、RiskManager、Reconciler の組立てを実装。RiskManager にデフォルト RiskConfig を提供（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）。
  - ExecutionEngine の PID ファイル・停止フラグの連携。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用ロジック。sell_candidates を除外する挙動、"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）と、未知レジーム時のフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算ロジック。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り。
    - risk_based の場合は stop_loss_pct と risk_pct を使用した算出。

- 研究・ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算するための基盤を追加（関数 calc_momentum 等の設計、定数設定）。（実装途中の箇所あり）

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を提供。stdout ストリームハンドラ + 日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - LOG_DIR 環境変数 / 引数でログ出力先を変更可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を実装（psutil 利用）。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装（指定が None なら変更なし、例外時は警告を出す）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。指定期間の稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99.0%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）を設定。
    - DB パスは --db オプション / PAPER_TRADING_SQLITE_PATH / デフォルト順で解決。

### Changed
- 設計方針（明示）
  - DuckDB を分析用 DB として組み込み（多くの処理が DuckDB 接続を引数に受けるよう設計）。
  - 監視（monitoring）コンポーネントは環境に依存せず本番 monitoring DB（sqlite_path）に接続する方針。

### Fixed
- 環境読み込みの堅牢化
  - .env のパースでクォート・エスケープ、export プレフィックス、インラインコメントの扱い等を考慮して正しく読み込めるように改善。
  - .env の自動ロードで OS 環境変数の保護（protected）を導入し、既存の環境変数を意図せず上書きしないようにした。

### Security
- 機密値の取り扱い
  - config_setup の表示ではシークレット項目（トークン・パスワード）をマスクして表示。
  - .env ファイル作成時に「.env を絶対に Git にコミットしないこと」をコメントで明示。

### Notes / Known limitations
- research/factor_research.py や一部の高度な処理は実装途中（ファイル末尾が切れている/続きが想定される）。本リリースでは設計・定数・インタフェースを中心に含め、詳細実装は今後の作業予定。
- position_sizing, risk_adjustment の計算は lot_size が全銘柄共通である前提。将来的に銘柄別単元対応への拡張が予定されている（TODO コメントあり）。
- PRICE 欠損時の挙動（price が 0.0 の場合の取り扱い）についてはコメントで注意が記載されており、フォールバック価格ロジックは未実装。

---

参照:
- デフォルトの重要な環境変数:
  - MONITOR_POLL_INTERVAL=60（run_monitoring）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_DIR=logs/
  - KILL_FLAG_CLEAR_ON_START=0（推奨）
- CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やプロジェクト方針に合わせて追記・修正してください。）