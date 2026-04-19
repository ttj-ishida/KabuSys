# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG はソースコードから推測して作成した要約です。実際のコミット履歴に依存していないため、細部は実装差分と異なる場合があります。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

Added
- 初回リリース相当の機能群を追加。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止はプロジェクト直下の data/stop_requested.flag によるフラグで制御。Monitoring は環境にかかわらず本番の sqlite_path を使用する仕様。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用の専用 SQLite（data/paper_trading.db）に記録。実行中の PID 管理（data/execution.pid）や停止フラグチェックに対応。
- 設定・起動補助 CLI
  - config_setup: .env の対話型ウィザードを追加。複数の設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch 等）を対話的に作成・更新可能。
  - validate_config: .env および config/*.yaml の静的検証ツールを追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
- 環境変数/設定管理
  - config.Settings クラスを導入。多数のプロパティで環境変数値を取得・検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。paper_trading 用 DB パスや監視閾値等をプロパティ経由で提供。
  - .env 自動読み込み機能を導入（プロジェクトルートが .git または pyproject.toml を基準に検出されれば自動読み込み）。既存 OS 環境変数は保護され、.env.local で上書き可能。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）。スコア全0時は等金額配分にフォールバックして警告をログに出力。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（既存ポジションを考慮し上限超過セクターの候補を除外）、市場レジームに基づく乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知のレジームはフォールバック）。
  - portfolio.position_sizing: position sizing ロジックを実装（risk_based / equal / score）。単元（lot_size）丸め、1銘柄上限や総投下上限（aggregate cap）、cost_buffer を考慮した保守的見積りとスケールダウン・余剰配分ロジックを実装。
- ユーティリティ
  - utils.logging_setup: ルートロガーの初期化ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。ログ全体を一度クリアして二重設定を防止。
  - utils.process_priority: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows/Linux/macOS 向けに差分吸収（psutil ベース）、アクセス制限や未対応環境では警告を出してスキップ。
- 監視・モニタリング
  - monitoring DB 初期化（init_monitoring_db の呼び出しにより監視テーブルの存在を保証）。run_monitoring と run_execution の両方で監視テーブルを冪等に初期化。
- Execution 系コンポーネント（起動スクリプトから組み立てる主要コンポーネントを追加）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（および RiskConfig / EngineConfig）等、ExecutionEngine を構成する主要モジュールを追加（起動時に依存注入してスレッド実行）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。期間フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。P95 の計算や各種閾値（稼働率99%、Fill 90%、Send 95%、P95 latency 200ms）を定義。
- 研究（research）
  - research.factor_research: DuckDB を利用したファクター計算モジュール（Momentum/Value/Volatility/Liquidity の設計骨子、モメンタム計算関数の追加を開始）。DuckDB 接続を受け取り SQL + Python で計算する設計。

Changed
- ログ出力方針: コンソールは stdout を使用（stderr ではない） — タスクスケジューラや cron からのリダイレクトを想定。
- 環境読み込みの優先順位を明確化: OS 環境 > .env.local > .env、かつ OS 環境は保護され上書きされない。

Fixed
- 環境変数の不正値に対する堅牢性強化:
  - MONITOR_POLL_INTERVAL が不正（整数変換不能や <= 0）の場合にデフォルトへフォールバックし警告を出力（run_monitoring）。
  - PAPER_FILL_MODE の検証処理を追加し不正値で ValueError を発生させる（Settings.paper_fill_mode）。
  - KABUSYS_ENV / LOG_LEVEL の不正値検出と説明付き例外を追加（Settings.env / log_level）。
- 起動時のリソースクリーンアップ: run_monitoring/run_execution で DB 接続（sqlite3, duckdb）を finally ブロックで確実に close。

Security
- .env の取り扱いについて注意を明記（config_setup にて .env を絶対に Git にコミットしない旨をファイルヘッダに記載）。

Notes / Implementation details
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明示しているため、監視データは環境によらず共通 DB に蓄積される設計になっている。
- run_execution は paper_trading 環境時に DB を完全分離（paper_sqlite_path）し、本番 DB と記録を混在させない運用を想定している。
- position_sizing の aggregate cap スケーリングは lot_size 単位で丸め、余りは残差（fractional remainder）が大きい順で lot 単位を追加配分するアルゴリズムを採用している（再現性のため同一残差時はコードで安定ソート）。
- apply_sector_cap は sector_map にコードが存在しない（"unknown"）銘柄はセクター上限の対象外にする振る舞い。
- process_priority/set_cpu_affinity は psutil に依存しており、権限不足等で失敗した場合は警告ログを出して処理を続行する。

署名
- 初期バージョン: __version__ = "0.1.0"

もし実際の変更履歴（コミット単位）や日付、より詳細な差分が必要であれば、Git のログやタグ情報を提供してください。そこからコミットメッセージに基づくより厳密な CHANGELOG を作成します。