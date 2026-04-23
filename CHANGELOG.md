# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初回公開: KabuSys パッケージの基盤機能を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 停止にはプロジェクトの `data/stop_requested.flag` を参照。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する挙動を採用。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを使用）。
    - SQLite と DuckDB 接続を確立し、監視用テーブルの初期化を行う。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離（デフォルト: `data/paper_trading.db`）。
    - BrokerClientFactory を用いて環境に応じた BrokerClient を生成（MockBrokerClient を含む実装想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - 起動時・実行中ともに `data/stop_requested.flag` を監視して安全に停止処理を行う。
    - 実行 PID を `data/execution.pid` に書き出す仕組み（Engine 側で pid_file を受け取る）。

- 設定・環境変数管理
  - config.py
    - Settings クラスを導入し、環境変数経由で設定値を提供。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - `.env` と `.env.local` の読み込みルール（OS 環境変数を保護、.env.local は上書き可能）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading 等）。
    - `paper_fill_mode` の妥当性チェック（instant/partial/never/reject）。
    - 環境判定プロパティ（is_live / is_paper / is_dev）等。

  - config_setup.py
    - インタラクティブな `.env` 作成ウィザードを追加。
    - 対話形式で主要な環境変数を入力し `.env` を生成・更新する機能。
    - シークレット値のマスク表示、選択肢・デフォルト・説明の提示。
    - 生成される `.env` のテンプレート（J-Quants, kabu, DB, LINE, KILL_FLAG など）を出力。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL / DB パスの妥当性チェック、config/*.yaml の存在・パース検証（PyYAML があればパースも実行）。
    - `--strict` オプションにより警告を失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の危険設定などを警告）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決、ログディレクトリ作成失敗時のフォールバック処理を実装。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。

  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）や CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。アクセス拒否などの場合は警告してスキップ。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築（純関数ユーティリティ）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）、等配分 calc_equal_weights、スコア加重 calc_score_weights（スコア合計0のフォールバック警告を含む）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 apply_sector_cap（既存ポジション時価からセクター露出を算出し、上限超過セクターの新規候補を除外）。
    - レジームに応じた資金乗数 calc_regime_multiplier（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - 複数の配分方式（"risk_based" / "equal" / "score"）に基づく発注株数計算 calc_position_sizes を実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、cost_buffer を考慮した aggregate cap スケーリングロジックを搭載。
    - risk_based モードでは risk_pct・stop_loss_pct を用いたリスクベース算出。
    - スケールダウン時の端数処理（残差に基づく lot 単位の追加配分）で再現性を確保。

- データベース・分析基盤
  - DuckDB 統合
    - DuckDB 接続を用いる設計（duckdb_conn を起動スクリプトや分析ツールに注入）。
  - 監視 DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルの冪等初期化を行うコードを各起動スクリプトで実行。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - CLI 引数（--from, --to, --db）で期間・DB を指定可能。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。

- 研究モジュール（開始実装）
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、流動性などを想定）。DuckDB の prices_daily / raw_financials を参照する方針。
    - モメンタム計算のための定数・設計方針を導入（実装は継続中、部分的に追加）。

### Changed
- N/A（初回リリースのため既存機能の変更はありません）

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

---

注:
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます。テスト等で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- config/*.yaml の内容検証は PyYAML のインストール状況に依存します。PyYAML がない場合はファイル存在チェックのみ行い、パース検証はスキップされます（validate_config.py にて警告）。
- 本リリースは初期実装を多数含むため、実運用前に validate_config による検証と config_setup による設定確認を推奨します。