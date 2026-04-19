CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記載します。
形式は「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- 全体
  - 初期リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバックして警告を出力。
    - 停止制御ファイル（data/stop_requested.flag）を検知してシャットダウン。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用の `sqlite_path` を使用して接続。
    - DuckDB との接続を確立し、監視用 DB 初期化を行う（init_monitoring_db）。
    - プロセス優先度を設定（utils.process_priority.set_process_priority）。

  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用 SQLite（`data/paper_trading.db`）に記録して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定値を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止。PID ファイル管理（data/execution.pid）。
    - DuckDB と SQLite の接続管理および監視テーブルの冪等初期化。

- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` と `.env.local` の読み込み順・上書きルールの実装。OS 環境変数は保護（protected）される。
    - .env 行パーサを実装（export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
    - Settings クラスを実装し、環境変数の取得と検証ロジックを提供（J-Quants / kabu API / LINE / DB パス / 各種閾値 / KABUSYS_ENV / LOG_LEVEL 等）。
    - `PAPER_FILL_MODE` の許容値チェック（"instant" | "partial" | "never" | "reject"）とエラー扱い。
    - パスプロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path 等）を Path 型で提供。
    - 便利なフラグプロパティ（is_live, is_paper, is_dev）。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを実装。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE トークン 等）と入力検証・マスク表示を提供。
    - 既存 .env の読み込み・再利用、確認プロンプト後に `.env` を書き込み。

  - validate_config.py
    - 起動前設定検証 CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML が利用可能な場合はパース検証を実行。
    - 本番（KABUSYS_ENV=live）に対する追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START が危険な設定になっていないかの警告）。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークルールで上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックして警告。

  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限（max_sector_pct）を超える場合に新規候補を除外。unknown セクターは除外しない仕様。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に基づく投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた注文株数決定ロジックを実装。
    - リスクベース計算、単元株（lot_size）丸め、1銘柄上限・aggregate キャップ（available_cash）スケーリング、cost_buffer による保守的見積り、残余キャッシュを利用した端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力、将来的な拡張（銘柄別 lot_size など）に関する TODO コメントを追加。

- ユーティリティ
  - utils.logging_setup
    - 統一ロギング初期化ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定。
    - 既存ハンドラの二重設定を防止するため既存ハンドラをクリアする挙動。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils.process_priority
    - クロスプラットフォームのプロセス優先度設定を実装（Windows の priority class / POSIX の nice を扱う）。AccessDenied 等は警告にフォールバックしてスキップ。
    - CPU affinity を最初の N コアにピンニングする set_cpu_affinity を実装（例外時は警告にフォールバック）。

- ツール
  - tools.paper_verification_report
    - ペーパートレード用検証レポート生成スクリプトを実装（期間指定可能、PAPER_TRADING_SQLITE_PATH 環境変数対応）。
    - システム安定性（稼働率 / エラー数）、注文成功率（fill/send rate）、リスク却下数、API レイテンシ（avg/max/P95）を算出してレポート出力。
    - P95 の計算、閾値に基づく PASS/FAIL 判定（デフォルト閾値をソースに定義）。

- リサーチ（計算基盤）
  - research.factor_research
    - ファクター計算モジュールの骨格を実装（モメンタム・MA200・ATR・流動性等を計画）。DuckDB 接続を受け取り prices_daily / raw_financials を使用する設計方針を記述。
    - calc_momentum の実装開始（関数シグネチャとドキュメント記載、計算パラメータ定義）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Security
- （該当なし）

Notes / Implementation details
- 監視・実行スクリプトはプロセス優先度設定や停止フラグ、PID 管理、DB 初期化等の運用上の配慮を取り入れています。環境変数や .env に敏感な情報（API トークン等）は .env に格納し、.env は決してリポジトリにコミットしないでください（config_setup の出力にも注意書きあり）。
- Paper Trading と Live は DB を分離しており、paper_trading 実行時は専用 SQLite を使用して本番 DB とデータを混ぜない設計です。
- ロギング周りはデフォルトで logs ディレクトリに日次ローテーションのログを出力しますが、ディレクトリ作成に失敗した場合はコンソールのみで継続します。

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースプロセスに合わせて日付や詳細は調整してください。）