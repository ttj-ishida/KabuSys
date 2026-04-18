CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

[0.1.0] - 初回リリース
---------------------

Added
- 実行用スクリプト・CLI を追加
  - run_execution: ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出す）。
    - エンジンはスレッドで実行され、data/stop_requested.flag により安全に停止可能。実行中の PID は data/execution.pid に保存する設計を想定（pid_file パスは設定から取得）。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や変換不能）の場合はデフォルトにフォールバックし警告を出す。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを一元保存。
    - 停止は data/stop_requested.flag により行う。
  - kabusys.validate_config: 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML があれば）等を実施。
    - --strict モードで警告を FAIL 扱いにできる。
  - kabusys.config_setup: .env を対話式に作成・更新するウィザードを追加。
    - J-Quants / kabuAPI / DB パス / ログレベル / Kill Switch 等の主要項目を対話で入力し .env を生成。
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - デフォルトの DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
- 設定管理 / 環境変数読み込み機能を強化（kabusys.config）
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に自動で探索し、.env/.env.local を読み込む（テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
  - .env パーサを独自実装し、以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート付き値（バックスラッシュエスケープ対応）
    - クォートなし値のインラインコメント判定（'#' の前がスペースまたはタブの場合はコメントと認識）
  - 環境変数の読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。OS 環境を保護するための protected set を利用。
  - Settings クラスを導入し、アプリから一貫して設定値を取得可能に。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE など）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）および is_live/is_paper/is_dev プロパティ。
- ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）
  - setup_logging(app_name, log_dir, level) を提供。
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定。
  - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト logs/。ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - 既存ハンドラの二重登録を防ぐため、設定時に一度ハンドラをクローズしてから再設定する。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority(level: high|normal|low): Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。権限不足や未対応 OS は警告を出してスキップ。
  - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピン留めする機能。引数検証あり。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: signal をスコア降順にソートし上位 N を返す（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等分にフォールバックして WARNING を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクター別時価を算出し、上限を超えるセクターの候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバックし WARNING を出す。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer（コスト緩衝）考慮、スケーリング時の端数配分ロジックを実装。
    - 価格欠損時はスキップし適切にログ出力。
- 研究用ファクター計算の下地を追加（kabusys.research.factor_research）
  - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計。モジュール内に各種定数（窓幅等）を定義。モメンタム計算関数のスタブを含む（calc_momentum 等）。
- Paper Trading 検証ツールの実装
  - 検証閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
  - DB からシステム稼働情報（system_status）、注文ログ（trade_logs）、リスクログ（risk_logs）を集計してレポートを出力。データ欠如時は N/A 表示。

Changed
- ログ出力先を stdout に統一（StreamHandler を stdout に設定）。cron 等でのリダイレクト運用を想定し stderr ではなく stdout を使用する方針を採用。
- .env 読み込みの保護機構を導入（OS 環境変数はデフォルトで上書きされない）。
- run_monitoring は監視 DB の初期化（init_monitoring_db）を実行し監視テーブルの存在を保証する（冪等）。

Fixed
- 環境変数解釈の厳密化:
  - MONITOR_POLL_INTERVAL の不正値に対しては警告を出してデフォルトにフォールバックするように変更し、time.sleep に不正値が渡らないように対処。
  - PAPER_FILL_MODE の不正値は明示的にエラー（ValueError）を送出するバリデーションを追加。
- プロセス優先度 / CPU affinity 設定において、未サポート OS や権限不足を例外で破壊しないよう try/except で安全化し警告に置き換え。

Notes / Implementation details
- DB パスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- run_monitoring の停止判定はプロジェクトルートの data/stop_requested.flag を参照（run_execution も同様）。
- ログは日次ローテーションで 30 世代まで保持。ログディレクトリの作成に失敗した場合はコンソール出力のみで動作を継続。
- position_sizing の aggregate スケーリングは可用現金を超過する場合にスケールダウンし、残余キャッシュで lot_size 単位の追加配分を行い再現性を保つために（fractional_remainder, code）でソートする戦略を採用。
- 一部モジュール（research 等）は計算ロジックの骨格を実装しているが、完全なテスト・最適化は今後の課題。

Security
- .env は決してリポジトリへコミットしない旨を config_setup のヘッダに明記。

今後の課題（留意点）
- position_sizing の価格欠損時（price == 0.0）の扱い: 将来的には前日終値や取得原価でのフォールバックを検討。
- ログディレクトリ作成失敗時のフォールバック診断を UX 向上のため改善可能。
- factor_research の各ファクターの最終チューニング・テストの追加。
- BrokerClient のモック実装と paper_trading の自動化テスト整備。

---