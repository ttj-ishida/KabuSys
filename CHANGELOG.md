# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
慣例: 変更のカテゴリは Added / Changed / Fixed / Removed / Security を使用します。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、設定管理ツール群、および検証用スクリプトを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して、本番 DB と完全に分離。
    - BrokerClientFactory を利用したブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで実行され、data/stop_requested.flag の検知で安全に停止する。実行時の PID を data/execution.pid に保存する仕組み（Engine 側の pid_file を利用）。
    - RiskManager にデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を追加。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下は無効扱いでデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用（監視データは本番 DB を想定）。
    - stop flag (data/stop_requested.flag) による終了判定や KeyboardInterrupt のハンドリングを実装。

- 設定周り
  - config.Settings: 環境変数からの設定取得クラスを追加。
    - J-Quants / kabuステーション / LINE / DB（DuckDB / SQLite） / 各種閾値 / PID / Kill flag 設定等をプロパティとして提供。
    - `env` の検証（development / paper_trading / live のみ許容）、`log_level` 検証、`paper_fill_mode` の検証（"instant"|"partial"|"never"|"reject"）などを実装。
    - `paper_sqlite_path` を提供し、paper_trading 用 DB を明示的に分離可能に。
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動ロード（OS 環境変数より低優先、.env.local は上書き）する仕組みを追加。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト等で利用）。
  - .env パーサーの改善
    - export KEY=val 形式、クォートあり (シングル/ダブル)、バックスラッシュエスケープ、インラインコメント処理、クォートなしの '#' コメント判定などをサポート。堅牢にパースするユーティリティを追加。
  - config_setup: 対話式 .env ウィザードを追加。
    - 初期 .env の作成／更新を支援。複数の設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE トークン / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）を対話的に入力可能。
    - シークレット項目はマスク表示。最終確認後に .env を書き込み（テンプレートヘッダを含む）。`.env` を Git にコミットしない旨の注意書きを出力。
  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェックと（PyYAML があれば）パース検証、live 環境時のガード（LINE 未設定や Kill flag の危険設定等）を実装。
    - 出力を errors / warnings / infos に分類。`--strict` を指定すると警告も失敗扱い（exit 1）にできる。
    - CLI から実行可能: python -m kabusys.validate_config

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（アプリ毎のログファイル、日次ローテーション、デフォルト 30 日保持）を設定。
    - LOG_DIR が作成できない場合はファイル出力をスキップし、コンソールのみで継続。既存ハンドラは再設定時に安全にクローズして置き換える。
    - stdout を使用することで外部スケジューラの出力扱いを容易に。
  - utils.process_priority
    - プロセス優先度設定 (high|normal|low) を Windows/Linux/macOS で抽象化して設定するユーティリティを追加。psutil を利用し、アクセス失敗時は警告ログでフォールバック。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（必要な権限がない場合は警告してスキップ）。

- データベース・分析基盤
  - DuckDB を利用するための接続箇所を追加（run_execution/run_monitoring で duckdb.connect 地点確保）。
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルが存在することを保証（冪等）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋signal_rank で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（全スコア 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を制限するフィルタ（売却予定コードを除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score） に基づき、単元株（lot_size）で丸めた発注株数を計算。個別上限・総合上限（available_cash）に対するスケーリング処理、cost_buffer による保守的見積り、残余分配ロジック（端数処理）を実装。

- 解析・検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）。
    - システム稼働率（system_status）、注文成功率（trade_logs）、リスク却下数（risk_logs）、レイテンシ指標（P95 等）を集計して PASS/FAIL 判定を行う。閾値はコード内で定義（稼働率 99% 等）。
    - P95 の計算、期間フィルタ（from/to 引数）のサポート、ファイル存在チェックと安全なクエリ実行を実装。
    - CLI から実行可能: python -m kabusys.tools.paper_verification_report

- research.factor_research (初期実装の序盤)
  - DuckDB 接続を受けてモメンタム等のファクターを計算するための基礎実装を開始（モメンタム計算関数の枠組み、定数定義）。※ ファイル末尾で処理が途中（未完）になっている部分あり。

### Changed
- Logging の挙動設計
  - 標準出力にログを出す際に stdout を使用する設計に変更（stderr ではなく）。ログファイルは日次ローテートで保管。

- DB パスの扱い
  - 実行／監視で DuckDB と SQLite の接続を明示的に確保するように変更。paper_trading 時の DB 分離を明示化。

### Fixed
- .env パースの堅牢化
  - クォート・エスケープ・インラインコメント等の扱いが改善され、不正なパースによる設定欠落を防止。

- ポジションサイズ計算のスケーリング／丸めロジック
  - aggregate cap を超える場合のスケーリング後、lot_size 単位での再配分アルゴリズムを実装し、端数処理の公平性と再現性を改善。

### Removed
- なし（初回リリース）

### Security
- 初版リリースの段階でセキュリティ関連の特別な修正はありません。機密情報（API トークン等）は .env 経由で管理し、config_setup は .env を Git に含めない旨の注意を出力します。運用時は .env の権限管理・秘密情報の取り扱いに注意してください。

---

補足:
- 本 CHANGELOG はソースコードから推測して記載しています。内部実装の詳細や将来の修正により挙動が変わることがあります。必要であれば個別ファイル単位の変更点（関数仕様や環境変数の具体例）を追記します。