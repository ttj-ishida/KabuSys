# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

なお、本 CHANGELOG は提供いただいたコードベースの内容から機能追加・設計意図を推測して作成しています。

## [Unreleased]
- 小さな改善・内部リファクタリング（ドキュメント整備やログ出力の安定化など）。

## [0.1.0] - 2026-04-22
最初のリリース（初期実装）。自動売買システム KabuSys のコア機能を実装・提供します。

### Added
- 実行・監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - ストップ用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用の SQLite（data/paper_trading.db）を使い、MockBrokerClient を利用する想定（BrokerClientFactory 経由）。
    - 依存コンポーネント（OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立て起動。
    - duckdb を分析用 DB として接続。
    - プロセス優先度を High に設定して実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視 DB（SQLite）は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグや KeyboardInterrupt を検知して安全に終了。

- 環境設定関連
  - config.py
    - .env 自動読み込み機構（プロジェクトルートを .git / pyproject.toml から検出）を実装。
    - .env パーサは export KEY=val、クォート、エスケープ、インラインコメントなどに対応。
    - Settings クラスを提供し、環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL など）をプロパティで行う。
    - 各種環境変数のデフォルト（DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）を定義。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を実装。
    - シークレット入力のマスク表示、既存 .env 読み込み、保存確認、.env 書き込みフォーマットを提供。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検査（PyYAML の有無を考慮）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから共通利用できるログ設定関数 setup_logging を実装。
    - コンソール（stdout）出力の StreamHandler と、日次ローテーション（TimedRotatingFileHandler、30日保持）でのファイル出力を組み合わせる。
    - ログディレクトリの自動作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。
    - set_cpu_affinity を提供し、利用したいコア数で CPU affinity を固定する機能を用意。
    - 権限不足や未サポート OS の場合は警告ログを出力して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）による候補選定 select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし WARN）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - リスクベースの算出（risk_pct, stop_loss_pct に基づく）、単元株（lot_size）での丸め、銘柄単位の上限（max_position_pct）を考慮。
    - 全体投下金額が使用可能現金を超える場合はスケールダウンし、小数端数の扱いのための残差(フラクション)順で追加配分を行う詳細アルゴリズムを実装。
    - cost_buffer による手数料・スリッページバッファ対応。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（当日売却予定銘柄を除外できる、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバックし WARN）。

- execution / monitoring 周辺
  - run_execution と run_monitoring で SQLite（監視／paper_trading 用）と DuckDB を組み合わせて使用する設計。
  - init_monitoring_db を利用して監視テーブルが存在することを冪等的に保証。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を Execution 起動時に設定。

- Paper Trading 用ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種検証指標（稼働率、注文成功率、送信率、レイテンシなど）を集計し、閾値（稼働率 >=99%、Fill>=90%、Send>=95%、P95 <=200ms）に基づき PASS/FAIL 判定を出力するレポート生成スクリプトを実装。
    - P95 計算、期間指定（--from / --to）、DB パス指定（--db / 環境変数）に対応。

- 研究系（factor 計算）基盤
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行うための設計・定数を定義。
    - DuckDB 接続を受け取り SQL と Python で計算する方針を実装（calc_momentum の実装開始）。
    - 戦略説明書（StrategyModel.md / PortfolioConstruction.md）に準拠した設計。

- パッケージメタ情報
  - __init__.py にてパッケージ version を "0.1.0" に設定。

### Changed
- 新規リリースのための初期実装群。既存コードからの大きな互換性破壊はなし（初版）。

### Fixed
- N/A（初期リリース）。

### Security
- 環境変数に秘匿値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を想定し、config_setup の .env は Git にコミットしない旨を明記。

---

備考:
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
- 監視関連は、run_monitoring が本番 sqlite_path を常に使う旨の注意（モニタリングは環境に依らず本番 DB を参照）に留意してください。
- この CHANGELOG はコードから推測したものであり、実際のリリースノート作成時にはリポジトリ履歴（コミットログ）や変更者の意図を確認して更新してください。