# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはリポジトリ内の最近の機能追加・設計意図・動作仕様をコードから推測してまとめたものです。

## [0.1.0] - 2026-04-25 (Initial release)
最初の公開バージョン。システム全体の起動スクリプト、設定管理、ロギング・プロセス制御ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどの基盤機能を実装しました。

### Added
- パッケージ全体
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログ出力。
    - 監視は実行環境に関係なく本番用 `sqlite_path` を使用して DB を初期化（init_monitoring_db を呼び出す）。
    - stop フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - プロセス優先度を High に設定して起動。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使い、本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドでセッションを実行。
    - 起動時 / 実行中に data/stop_requested.flag を検知してエンジンを停止。
    - 実行 PID ファイル管理（data/execution.pid）。
    - プロセス優先度を High に設定して起動。
- 設定 / 環境読み込み
  - config.py
    - 環境変数・設定管理クラス `Settings` を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づいて `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースは export プレフィックス、引用符、エスケープ、インラインコメント（クォートなし時の扱い）に対応する堅牢な実装。
    - 各種プロパティを用意（J-Quants / kabu / LINE / DB パス / 監視閾値 / システム環境判定 等）。PAPER_FILL_MODE の妥当性チェックなど。
    - `settings = Settings()` で簡便に使用可能。
  - config_setup.py
    - 対話式 `.env` 作成・更新ウィザードを提供。
    - デフォルト値や選択肢、シークレット入力の取り扱い、既存 .env の読み込み・再利用、最終確認・保存に対応。
    - 標準的な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を網羅。
  - validate_config.py
    - 起動前検証 CLI。`.env` および config/*.yaml の存在や基本的妥当性をチェック。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在および PyYAML がある場合はパース検証、`live` 環境向け追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - `--strict` オプションで警告を FAIL として扱うモードをサポート。
- ログ / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティ `setup_logging(app_name, log_dir, level)` を実装。
    - stdout への StreamHandler（stdout を使用する点に注意）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定 `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）で適切な nice / priority を設定。権限や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を提供（利用可能なコア数チェックと例外ハンドリング）。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates(buy_signals, max_positions)`（スコア降順、タイブレークは signal_rank）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコア総和が 0 の場合は等金額配分にフォールバックして warning）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap(...)`（既存保有のセクター時価比率が上限を超える場合、新規候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier(regime)`（"bull"/"neutral"/"bear" → 1.0/0.7/0.3、未知のレジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes(...)` を実装（allocation_method: "risk_based"|"equal"|"score"）。
    - risk_based: リスク許容率、ストップロス等に基づく株数算出。
    - equal/score: 各銘柄のウェイトに基づく算出。
    - 単元株（lot_size）の丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に対するスケールダウンロジック、cost_buffer（手数料/スリッページ見積り）を考慮した挙動。
    - スケールダウン後の残余キャッシュで fractional 残差が大きい順に lot 単位で追加配分するアルゴリズムを実装。
  - portfolio/__init__.py で主要関数群をエクスポート。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプト。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などの抽出・集計。
    - P95 計算ユーティリティ、期間フィルタ（ISO8601 UTC 文字列化）、閾値に基づく PASS/FAIL 判定（デフォルト閾値をソース内で定義）。
    - CLI 引数 `--from`, `--to`, `--db` に対応。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を実装（モメンタム / MA200 / ATR / ボリューム等の計算を想定）。DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計。
    - 定数（ウィンドウ長等） を定義し、calc_momentum などの計算関数を実装する方針を示す（ファイル末尾は途中で切れているため部分実装の可能性あり）。

### Changed
- ドキュメント的注記・仕様
  - 各モジュールに詳細な docstring と設計意図を追加（挙動、入力/出力、想定ユースケース、将来の拡張案など）。
  - ログ出力は統一されたフォーマットと日次ローテーションを想定。

### Fixed
- 環境変数パースの堅牢化
  - .env の行解析で引用符内のエスケープ処理、export プレフィックス、インラインコメントの扱いを改善（config._parse_env_line）。
- 実行安全性
  - run_execution/run_monitoring 両スクリプトで DB 接続を finally ブロックで確実にクローズするように実装。

### Notes / Behavior highlights
- 環境変数関連（代表的なもの）
  - KABUSYS_ENV: 有効値は development / paper_trading / live。Settings.env で検証。
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。不正値はデフォルト 60 にフォールバック。
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）。無効値は例外。
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite。paper_trading 実行時に使用。
  - KILL_FLAG_CLEAR_ON_START: 本番環境での Kill Switch 自動クリアを制御（推奨は 0）。
  - LOG_DIR / LOG_LEVEL: ロギングの挙動を制御。
- 停止制御
  - data/stop_requested.flag を監視して run_* スクリプトが優雅に終了/停止する仕組みがある。
- DB 初期化
  - monitoring 用テーブルは起動時に init_monitoring_db を呼び出して冪等に初期化される（存在確認を保証）。
- 権限・プラットフォーム差
  - process_priority/set_cpu_affinity は権限や OS により動作しない場合があるが、失敗時は警告ログを出してスキップする設計。

---

将来のリリースで次のような改善が想定されます（コード中の TODO／コメントに基づく）:
- position_sizing に銘柄別 lot_size サポート（stocks マスタからの取得等）。
- price のフォールバック（前日終値や取得原価）を用いた exposure 計算改善。
- research/factor_research の完全実装とユニットテスト追加。
- 監視・実行のより詳細なメトリクス収集・アラート強化。

------------------------------------------------------------------------------
（以上）