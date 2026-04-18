# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠で管理しています。

全般的なルール:
- 変更はカテゴリ別に整理（Added, Changed, Fixed 等）
- 可能な限り該当ファイルや CLI 名を明記

## [0.1.0] - 2026-04-18

### Added
- 初回リリースを追加（パッケージバージョン: 0.1.0）。
- 実行用スクリプト/サービス
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止はプロジェクト data/stop_requested.flag の検出で行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を想定）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db を使用して本番 DB と完全分離。
    - ExecutionEngine をバックグラウンドスレッドで起動し、stop flag で優雅に停止可能。
    - PID ファイル管理（data/execution.pid）をサポート。
- 設定関連
  - config.py: 環境変数／.env 自動ロード機能、堅牢な .env パーサー、および Settings クラスを追加。
    - .env ファイルの自動読み込み順: OS 環境 > .env.local > .env。プロジェクトルート検出ロジック（.git / pyproject.toml ベース）。
    - 引用符やエスケープを考慮した行パース、 `export KEY=val` 形式に対応。
    - 各種設定プロパティを提供（DB パス、paper_trading 用 DB、閾値、PID/kill flag パス、API トークン等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py: 対話式の .env 作成ウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベルなど主要項目を対話的に生成・保存。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パスと config/*.yaml の存在/パース確認、live 専用ガード等。
    - --strict モードで警告を失敗扱いにできる。
- ロギング & プロセスユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。
    - stdout StreamHandler と 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）に対応するラッパー。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足等は警告でスキップ。
- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコアでソートして上位 N を選択（同点タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく新規候補の除外ロジックを追加（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear のマッピング、未知レジームは警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき、単元株（lot_size）丸め・max_position 上限・aggregate cap（available_cash）に従ったスケーリングを実装。
    - cost_buffer（手数料/スリッページ考慮）や lot 単位での再配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルトの DB は data/paper_trading.db。CLI で日付範囲と DB パスを指定可能。
    - 判定基準（稼働率 99%, 成功率 90% など）を定義し PASS/FAIL を出力。
- 研究用モジュール（未完を含む）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。
    - calc_momentum 関数の骨格を実装（DuckDB 接続を受け取り prices_daily などを参照する設計）。※ファイル末尾で未完の箇所あり（実装継続予定）。

### Changed
- パッケージ初期構成としてモジュール分割を整備（execution, monitoring, portfolio, utils, research, tools 等をエクスポート）。
- 実行スクリプトは起動時にプロセス優先度を設定し、ログ設定を統一的に初期化するよう変更（setup_logging + set_process_priority 呼び出しを統一）。

### Fixed
- .env パースの強化:
  - 引用符付き値でのバックスラッシュエスケープ処理を適切に処理。
  - クォートなしでのインラインコメント判定を改善（'#' 前のスペースでコメントと認識）。
- SQLite / DuckDB 接続の初期化時に監視テーブルが存在しない場合でも init_monitoring_db() により冪等に作成するよう対処（init_monitoring_db の呼び出し箇所を追加）。

### Notes / Migration
- Paper Trading（KABUSYS_ENV=paper_trading）を使用する場合、SQLite DB は paper_sqlite_path（デフォルト: data/paper_trading.db）に切り替わります。既存の本番 monitoring.db とは分離して運用してください。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正な値や 0 以下はデフォルト（60秒）にフォールバックし、警告が出力されます。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト等で利用）。
- research/factor_research.py は一部未完の箇所があります。ファクター計算の完全実装は今後のリリースで追加予定です。

---

以上が本リリース（0.1.0）の主な変更点です。追加の詳細や補足が必要であればお知らせください。