# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
主にソースツリーの初期実装に基づき、機能追加・設計方針・運用上の注意点を推測してまとめています。

さらに詳細が必要な場合は該当ファイルを参照してください（src/kabusys 以下）。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 全体
  - プロジェクト初期実装を追加。パッケージ名は `kabusys`、バージョン `0.1.0`。
  - DuckDB と SQLite を併用するデータ基盤を前提としたアーキテクチャを導入（Path 設定は環境変数で上書き可能）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知によるグレースフルシャットダウン。
    - Monitoring は環境設定に関わらず本番用 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - SQLite / DuckDB 接続の初期化とクローズ処理を実装。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker を用いる設計（Paper Trading 用 DB に記録し本番と分離）。
    - 停止フラグ（data/stop_requested.flag）検知による Engine.stop() 呼び出しとプロセス終了処理。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。

- 設定管理
  - Settings クラスを実装し、アプリケーション設定値（環境変数）をラップして提供。
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値等のプロパティを用意。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）と PAPER_FILL_MODE のバリデーション。
    - PID ファイルや kill flag のパス・挙動を設定から取得可能。
  - .env の自動ロード機構を実装
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を読み込み。
    - OS 環境変数を保護する仕組みを採用（既存の OS 環境変数を上書きしない / .env.local は上書き可）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env のパースは export 形式・引用符・エスケープ・インラインコメント等に対応。

- 設定ユーティリティ・CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 各設定項目の説明、デフォルト、選択肢、シークレット扱いが可能。
    - 既存 .env の読み込みと Enter による再利用、保存前の確認をサポート。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV・LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境（live）向けのガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング / プロセス優先度
  - logging_setup: ルートロガーに対する一括設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を設定。
    - 既存ハンドラをクリアして二重追加を防止。
    - LOG_DIR/LOG_LEVEL 環境変数または関数引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: プロセス優先度（"high"/"normal"/"low"）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して nice 値や Windows 固有定数を使用（権限不足等は警告でスキップ）。
    - set_cpu_affinity によりプロセスを最初の N コアに固定可能（実行環境により未対応となる場合は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
    - calc_equal_weights: 等金額配分の重みを生成。
    - calc_score_weights: スコア加重配分。全てのスコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックして新規候補を除外するロジック。既存保有のエクスポージャ計算時に売却予定銘柄を除外可能。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）を提供。未知のレジームは警告の上 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数の allocation_method（"risk_based", "equal", "score"）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した安全弁を実装。

- Execution 周辺
  - run_execution から BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等の構成要素を組み立ててエンジンを起動する実装を追加（各コンポーネントは別ファイルに実装）。
  - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。初期ポートフォリオ値に Broker の get_available_cash() を使用。

- Paper Trading / 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）, リスク却下数 等。
    - デフォルトの判定閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数) をサポート。

- 研究モジュール（部分実装）
  - research.factor_research: DuckDB から価格・財務データを参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算するための枠組みを追加（関数シグネチャと定数が定義され、一部関数は実装途中）。

### Changed
- （初期リリースのため過去変更はなし。実装上の設計注記をドキュメント的に追加）
  - Monitoring と Execution の DB 接続ロジックで、監視データの初期化（init_monitoring_db）を冪等に実行してテーブル存在を保証。

### Fixed
- （初期リリースのためバグ修正履歴はなし）

### Removed
- （該当なし）

### Security
- 環境変数の自動ロードで OS 環境変数を上書きしない保護機構を導入（.env の上書き設定に対して保護対象指定を行う）。  
- .env ファイルは出力時に「絶対に Git にコミットしないこと」を注意書きとして明確化。

### Notes / 運用上の注意
- run_monitoring は Monitoring 用に「本番 sqlite_path」を使用するため、運用時は KABUSYS_ENV にかかわらず監視対象データベースの配置・権限に注意してください。
- run_execution は paper_trading 環境では paper_trading 用 DB（data/paper_trading.db）に完全分離してデータを残す設計のため、本番 DB と混同しないよう注意してください。
- process_priority / cpu_affinity の設定は環境（OS 権限やプラットフォーム）に依存し、設定失敗時は警告を出して処理を継続します。
- .env の自動ロードが望ましくない環境（テスト等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config により起動前に設定チェックを行うことを推奨します（特に KABUSYS_ENV=live の場合は注意喚起が表示されます）。

---

上記はソースコードから推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴やリリースノートに合わせて日付や項目を調整してください。