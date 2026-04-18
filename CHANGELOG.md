# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構成ロジック、検証/設定用 CLI、分析ツール等を収録。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動ロジックを提供。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててエンジンを起動。停止フラグ（data/stop_requested.flag）と PID ファイルの管理に対応。
    - RiskConfig のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をコード上で定義。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視データは一元管理）。
    - 停止フラグの検知、例外時のログ出力とループ継続処理を実装。
- 設定管理・検証・ウィザード
  - config.py
    - .env の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - .env/.env.local の読み込み順、OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - .env の各行パーサーで export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 監視閾値 / 環境種別等のプロパティを安全に取得可能。PAPER_FILL_MODE の値検証（instant/partial/never/reject）等を行う。
  - validate_config.py
    - 起動前に必須環境変数・設定ファイル・パス等の検証を行う CLI を追加。--strict オプションで警告も失敗扱いにできる。
    - YAML パーサが存在しない場合は YAML 検証をスキップする（警告出力）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新するツールを追加。シークレット値のマスク表示、選択肢サポート、確認 → ファイル保存フローを実装。
- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保存）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフェイルセーフを実装。
    - ログレベル解決順（関数引数 > 環境変数 LOG_LEVEL > デフォルト）およびログディレクトリ解決順（引数 > 環境変数 LOG_DIR > デフォルト）を実装。
    - コンソール出力は stdout を使用（stderr ではない）。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定機能を追加（Windows / POSIX に対応）。AccessDenied 等のエラー時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価に基づき上限を超えるセクターの新規候補を除外。unknown セクターは制限適用対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method として `risk_based`（リスクベース）および `equal` / `score` をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケールダウン時の切り上げ配分アルゴリズム（残余キャッシュでの lot 単位追加配分）を実装し再現性確保のため安定ソートを使用。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）を解析して検証レポートを出力する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。デフォルト閾値をコードに定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ、P95 計算、欠損時のフォールバックを実装。
- research/factor_research.py
  - ファクター計算モジュール（Momentum/Value/Volatility/Liquidity 計算方針）を追加。DuckDB 接続を受け価格・財務データを用いる設計。モメンタム計算等の基礎関数を含む（当該モジュールはデータ依存のため DuckDB 上のテーブル構成に依存）。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログ出力・監視周りのデフォルト挙動を明確化
  - 監視スクリプトは MONITOR_POLL_INTERVAL を読み取り、1 秒未満や 0 などの不正値はデフォルト 60 秒にフォールバックして警告を出すように変更。
  - run_monitoring は環境に関係なく本番 sqlite_path を監視 DB として使用（監視データの一元化目的）。
- .env の読み込み順と上書きルールを明確化
  - OS 環境変数が優先され、.env.local は .env より後で上書き（override=True）される。os 環境変数は protected として .env による上書きを防止。
- 実行/監視起動時にプロセス優先度を最初に設定するよう統一（set_process_priority("high")）。

### Fixed
- ログファイルハンドラ作成に失敗した場合でもコンソールログが動作し続けるようにフェイルセーフを導入（例: ログディレクトリ作成失敗時）。
- .env パーサでのクォート内エスケープや export プレフィックス、インラインコメント処理を改善し、より現実的な .env フォーマットを許容。

### Security
- .env を生成するウィザードでシークレット項目はマスク表示するよう実装（.env の誤コミット防止を README 等で併せて推奨）。

### Notes / Operational
- KILL_FLAG_CLEAR_ON_START 環境変数を 1 にすると起動時に kill flag を自動クリアする挙動があるが、本番環境では危険なため validate_config にて警告を出す。
- PAPER_FILL_MODE の不正値は Settings レイヤで ValueError を発生させるため、起動前に正しい値を設定すること。
- DuckDB / SQLite のパスは環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）で上書き可能。validate_config により親ディレクトリの存在チェックなどを行うが、起動スクリプトは必要に応じてディレクトリを自動作成する場合がある。

---

今後の予定（例）
- research/factor_research の各ファクター実装の拡充とテストカバレッジ追加。
- strategy / execution の統合テスト・モックの拡張。
- 設定/ログのさらなる堅牢化とドキュメント整備。