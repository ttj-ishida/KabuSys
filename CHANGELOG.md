# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

※ 以下はリポジトリ内のコードから推測して作成した履歴です。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-19

初期リリース。自動売買システム KabuSys のコア機能とユーティリティを実装。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 実行中は data/stop_requested.flag を監視して安全に停止。
    - 実行 PID を data/execution.pid に保存（Engine 側で使用）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ検知でループ終了、KeyboardInterrupt に対応。

- 環境設定 / 検証 CLI
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 主要な環境変数（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を対話形式で入力。
    - シークレット項目は表示をマスクして保存。
    - .env 保存前に確認プロンプトを表示。
  - validate_config: .env や config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML インストール時）を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番（live）向けの追加警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定など）。

- 設定管理
  - config: 環境変数読み込み・管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml を基準に検出（CWD に依存しない）。
    - .env / .env.local の自動読み込み機能（OS 環境変数を保護して上書き制御）。
    - .env 行のパーサは export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメントを考慮して堅牢に処理。
    - Settings クラスで各種設定にアクセス可能（duckdb/sqlite のパス、paper_trading 用 DB、PID / kill flag /閾値等）。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）や KABUSYS_ENV の妥当性チェックを実装。
    - settings = Settings() として容易に参照可能に。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋ signal_rank によるタイブレークで選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（available_cash / max_utilization）を考慮。
    - cost_buffer を用いた保守的なコスト見積りと aggregate cap によるスケールダウン（端数配分の再配分ロジック含む）。

- ユーティリティ
  - utils.logging_setup:
    - 統一的なロギング設定を提供（setup_logging）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリの作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
    - 出力先として stdout を使用（cron 等のリダイレクトを想定）。
  - utils.process_priority:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供（失敗時は警告でスキップ）。
    - 権限不足や未サポート環境に対する堅牢な例外処理と警告表示。

- モニタリング / DB 初期化
  - monitoring.monitoring_db へ接続して監視テーブルの初期化を行う（冪等）。
  - SystemMonitor の単回チェック check_once() をポーリングループから呼び出す実装（例外発生時はロギングして継続）。

- ペーパートレード検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime%）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルトの合否基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - 日付フィルタ (--from / --to) と --db オプションを提供。
    - P95 計算、SQL クエリにおける NULL 安全性やテーブル未存在時のフォールバック処理を実装。

- リサーチ（部分実装）
  - research.factor_research:
    - ファクター計算の骨子を実装（モメンタム／MA200乖離／ATR／流動性等を計画）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。
    - calc_momentum 等の関数雛形を追加（実装はモジュール内で続くものを想定）。

### Changed
- なし（初期リリースのため）

### Fixed
- なし（初期リリースのため）

### Security / Notes
- .env は絶対に Git にコミットしないことを README 等で明記する想定（config_setup のヘッダに注意書きを追加）。
- いくつかの必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定の場合に起動・検証時にエラーを出す（validate_config と Settings._require が該当）。

### CLI / 利用方法（主要ポイント）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

開発上の補足・既知の制約（推定）
- portfolio.position_sizing は現状単元株数をグローバルに lot_size で扱う（将来的に銘柄毎の単元対応が必要）。
- apply_sector_cap の価格欠損（price_map に値がない場合）によりエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。
- process_priority / set_cpu_affinity は権限や OS によって実行できない場合がある（警告でスキップされる）。
- research モジュールはファクター計算の設計に基づく実装が続く想定で、一部関数は未完または拡張の余地あり。

もし特定の変更点やリリースノートの調整（例: 日付、詳細な破壊的変更の追記など）が必要であれば、その範囲に合わせて追記・修正します。