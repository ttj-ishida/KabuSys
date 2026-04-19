# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。
リリースはセマンティック・バージョニングに従います。

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期リリース。
- 実行系 / 監視系の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper トレード用の専用 SQLite(DB: data/paper_trading.db を想定) を使用するよう分離。
    - BrokerClientFactory を用いたブローカークライアントの生成。
    - Engine を別スレッドで実行し、data/stop_requested.flag による外部停止フラグを監視。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中は data/execution.pid に PID を書き込む想定（pid_file を受け取る）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化する。
    - data/stop_requested.flag による停止、KeyboardInterrupt ハンドリング。
- 設定管理・自動ロード機構
  - config.py
    - .env/.env.local の自動読み込み（OS 環境変数優先）。プロジェクトルートは .git または pyproject.toml を探索して検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - Settings クラスを提供し、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各しきい値等）をプロパティで取得。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）と便利プロパティ（is_live/is_paper/is_dev）。
- 環境設定ユーティリティ
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 標準項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を定義。
    - 秘匿値はマスク表示、Enter で既存値またはデフォルトを再利用可能。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 共通の setup_logging(app_name, log_dir, level) を追加。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日保持）によるファイル出力をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 環境変数を尊重し、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作。
- プロセス優先度・CPU affinity ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX (Linux/Mac/FreeBSD) に対応して優先度をセット。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) による CPU コア固定の補助。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、セクター上限を超過しているセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime ("bull"/"neutral"/"bear") に対する投下資金乗数を返す。未知のレジームは警告し 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score に対応した発注株数計算。単元株（lot_size）で丸め、1銘柄上限や aggregate cap（利用可能現金）を考慮してスケールダウンするアルゴリズムを実装。cost_buffer を考慮した保守的見積もり。
- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - Momentum 等のファクター計算意図・定義と定数（1M/3M/6M リターン、MA200 乖離、ATR、出来高など）を実装する設計。DuckDB を用いて prices_daily/raw_financials を参照する設計方針を明示。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py
    - Paper Trading DB（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率・注文成功率・送信率・レイテンシ(P95) 等を出力する CLI。
    - デフォルト基準値（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）を用いた PASS/FAIL 判定を実装。
    - --from / --to / --db オプション対応。
- パッケージメタデータ
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Changed
- 初回リリースのため履歴なし。

### Fixed
- 初回リリースのため履歴なし。

### Notes / 実装上の注意点・既知の制限
- config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを検出する。配布後や特殊な配置では検出されない可能性がある（その場合、自動 .env ロードはスキップされる）。
- apply_sector_cap: price_map に価格が欠損（0.0）があるとエクスポージャが過少見積りされ、想定より除外されない可能性がある（TODO コメントあり）。
- process_priority/set_cpu_affinity は権限やプラットフォームに依存し失敗する場合がある（失敗時は警告でフォールバック）。
- research/factor_research.py はモジュールの骨格と定数まで実装されているが、関数 calc_momentum 等の一部実装が途中で切れている（追加実装が必要）。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合は stdout のみでログを出力する。

---

（次回以降のリリースでは Unreleased セクションを設け、変更差分を追記してください。）