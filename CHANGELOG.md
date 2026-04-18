# Changelog

すべての重要な変更は Keep a Changelog に従って記載します。

## [Unreleased]

- -

## [0.1.0] - 2026-04-18

初回リリース（コードベースから推測して作成）。以下はソースコードの内容に基づく主な追加機能・実装の要約です。

### Added
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db、環境変数で上書き可）と完全に分離して動作する。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止する仕組みを実装。
    - 実行用 PID ファイル（data/execution.pid）管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する（監視テーブルの初期化を担保）。

- 環境設定・検証関連
  - config.py: Settings クラスを実装。環境変数や .env / .env.local の自動ロード（プロジェクトルートの検出に基づく）を提供。
    - .env の自動読み込みは OS 環境変数を保護する仕組みを持ち、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化が可能。
    - 環境変数のパースは export 形式・クォート・エスケープ・インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等）。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。秘密値のマスク表示や選択肢、デフォルト値をサポートし .env を書き出す機能を持つ。
  - validate_config.py: 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在・パース（PyYAML がインストールされている場合）を検証。`--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに対して統一的なセットアップを提供。
    - stdout への StreamHandler（stdout を使用して cron 等の出力統合に対応）。
    - 日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）を追加し、ログディレクトリの自動作成と 30 日分保持を実装。フォールバックでファイル出力無効化の扱いも行う。
    - ログレベル・ログディレクトリの解決順序を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX を吸収）と CPU affinity を設定するユーティリティを追加。psutil を用い、権限不足等に対しては警告を出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）と上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有が上限（デフォルト 30%）を超える場合、新規候補を除外するロジック。sell_codes（当日売却予定）を考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金倍率を返す（デフォルト値・unknown のフォールバックあり）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数の計算を実装。単元株丸め、1 銘柄上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。risk_based の場合は stop_loss を用いたリスク算出を行う。

- Execution 周りの内部統合
  - run_execution から呼ばれるコンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）を組み立て、デフォルトの RiskConfig（最大保有比率、利用率、レート制限、サーキットブレーカー、最大ドローダウン 等）を設定して ExecutionEngine を起動する実装（起動時に停止フラグが立っている場合は起動を中止）。

- 監視・運用ツール
  - monitoring_db の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring で冪等的に行い、監視テーブルの存在を保証。
  - run_monitoring のポーリングループは例外を捕捉してログ出力の上で次ポーリングへ継続する堅牢化を実装。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH または --db）から複数指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計し、しきい値に基づく PASS/FAIL レポートを生成するスクリプトを追加。
    - P95 計算、日付フィルタ、欠損時の N/A 表示、閾値はソース内定義（例: 稼働率 >= 99% 等）。

- research/factor_research.py（ファクター計算基盤）
  - DuckDB 接続を受けて momentum/value/volatility/liquidity 系ファクターを計算する設計のモジュールを追加（モジュールは未完部分あり）。各種定数（期間設定等）と calc_momentum の雛形を含む。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサーを改善（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）し .env の柔軟な読み込みに対応。

### Known limitations / Notes
- research/factor_research.py は一部未完（ファイル末尾で切れている）。ファクター計算全体の実装は追加作業が必要。
- position_sizing 等では価格が欠損（0.0）の場合のフォールバックが TODO としてコメントで残されている（前日終値や取得原価のフォールバック検討）。
- process_priority, cpu_affinity の設定は権限やプラットフォーム依存のため実行環境によりスキップされる場合がある（ログで警告される）。
- .env は機密情報を含むため Git にコミットしないことを強調（config_setup でヘッダに注意書きあり）。

### Security
- （初回リリースのため特記すべきセキュリティ修正はなし）

---

脚注:
- 上記 CHANGELOG は提供されたソースコードを基に推測して作成しています。実際のリリースノートや変更履歴はプロジェクトのコミット履歴やリリース管理ポリシーに合わせて調整してください。