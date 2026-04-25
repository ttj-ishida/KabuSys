# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のフォーマットに従って記載しています。意図しない動作や詳細は各モジュール内のドキュメント文字列を参照してください。

※ 本リポジトリの初回リリースをコードベースから推測してまとめています（バージョンは package メタ情報 __version__ に基づく: 0.1.0）。

## [Unreleased]

なし

## [0.1.0] - 2026-04-25

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - package version: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 実行/監視用起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、SQLite / DuckDB に接続。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド起動を実装。
    - data/execution.pid（デフォルト）を使用して PID ファイルを管理。data/stop_requested.flag による外部停止フラグ検出に対応。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 等）を組み込み。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の分離ポリシー）。
    - data/stop_requested.flag による停止フラグ検知、KeyboardInterrupt のハンドリングを実装。

- 設定管理/ウィザード/検証
  - config.py
    - Settings クラスを実装し、環境変数（および自動ロードされた .env/.env.local）から各種設定を参照する API を提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等の Path 型プロパティを提供。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）とバリデーションを実装。
    - KABUSYS_ENV の有効値チェック（development, paper_trading, live）や LOG_LEVEL のバリデーションを実装。
    - 自動的にプロジェクトルート（.git または pyproject.toml を起点）を探索して .env/.env.local を読み込む機能を実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 環境変数読み込みの保護（OS 環境変数を上書きしない / .env.local での上書きを許可）を実装。

  - config_setup.py
    - 対話式環境設定ウィザードを追加（.env の初期作成・更新を支援）。
    - 一連の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に入力・確認して .env を生成する。
    - secret 項目はマスク表示、選択肢/デフォルト/説明をサポート。
    - .env 書き込みテンプレート（`.env` に保存するためのヘッダ・注意書き）を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML を用いたパース検証）。
    - `--strict` オプションで警告を FAIL 扱いにする機能を提供。
    - 本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性チェック）を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout 出力の StreamHandler（stdout 指定）と日次ローテーションの TimedRotatingFileHandler（<log_dir>/<app_name>.log、デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順や引数 override を実装。

  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")：Windows（HIGH_PRIORITY_CLASS 等）、POSIX（nice 値）に対応し、例外時に警告を出す。
    - set_cpu_affinity(cpu_count: Optional[int])：最初 N コアに固定する機能を追加（アクセス不可時は警告でスキップ）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（score 降順、同点時 signal_rank 昇順）を実装。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全銘柄スコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap：既存保有のセクター別エクスポージャーを計算し、1 セクター上限（max_sector_pct）を超える場合に当該セクターの新規候補を除外するロジックを実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier：市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を提供（uncertain レジームは 1.0 フォールバック、未定義時は警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based"|"equal"|"score"）に応じて発注株数を計算する実装。
    - lot_size（単元株）で丸め、per-stock および aggregate の上限（max_position_pct, max_utilization）や cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング／端数処理を実装。
    - price が取得できない場合のスキップや既存保有との差分のみを発注対象とする挙動を実装。

  - portfolio/__init__.py
    - 上記の主要関数をパッケージエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- 研究用ファクター計算ユーティリティ
  - research/factor_research.py
    - DuckDB ベースでのファクター計算（Momentum / Value / Volatility / Liquidity）を想定した設計。prices_daily / raw_financials テーブル参照、Z スコア正規化は外部モジュール利用を想定している旨の API と定数を導入。
    - モメンタム関連の定数（21,63,126,200 日など）・スキャン範囲の定義を追加（calc_momentum の開始）。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - 指標計算: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/p95）等を SQL で集計して表示。
    - 判定基準（しきい値）を定義: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ (--from/--to) に対応。

- その他ユーティリティ
  - utils/__init__.py, tools/__init__.py などのパッケージ初期化を追加。

### Changed
- 初回リリースのため該当なし（新規追加のみ）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため特記事項なし。ただし .env ファイル生成に関する注意（.env を絶対に Git にコミットしない）や、KILL_FLAG_CLEAR_ON_START の設定が本番で危険である旨の警告をユーザ向けに実装。

---

補足:
- 自動読み込みされる .env ロード順は OS 環境 > .env.local > .env で、既存の OS 環境変数は保護される（上書きされない）設計です。
- ロギングは標準出力（stdout）に出力されるため、cron/Task Scheduler などでのリダイレクト運用に配慮しています。
- run_execution/run_monitoring は外部プロセス制御用に stop flag（data/stop_requested.flag）や pid ファイルを利用することで安全に外部から停止を要求できます。

もし追加でリリースノートに含めたい詳細（例: 各関数の API 例、既知の制限、移行ガイドなど）があれば教えてください。それを反映して CHANGELOG を拡張します。