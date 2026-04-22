# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは日本語で記載しています。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-11

### Added
- 基本アプリケーション骨格を追加
  - パッケージ情報: kabusys のバージョンを 0.1.0 に設定。
  - モジュール公開: portfolio, execution, monitoring 等の主要モジュールをエクスポート。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 DB (`data/paper_trading.db` または環境変数で指定) を使用して本番 DB と分離。
    - 停止フラグ (data/execution.pid / data/stop_requested.flag) による安全停止、PID ファイルの扱い、スレッド起動・監視のフローを実装。
    - RiskManager / OrderManager / OrderRepository / Reconciler の組み立てとデフォルトリスク設定（例: max_position_pct=0.20, max_utilization=0.80 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - 停止フラグ (data/stop_requested.flag) の検知でループを安全に終了。
    - 監視用途の DB 接続は環境に依存せず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py
    - 環境変数 / .env ファイルの自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env の読み込みロジックは OS 環境変数を保護しつつ、`.env`→`.env.local` の順で適切に上書き可能。
    - .env のパースでシングル/ダブルクォート内のバックスラッシュエスケープや、非クォートのインラインコメント処理など細かな仕様に対応。
    - Settings クラスを導入し、各種設定（DB パス、API トークン、PaperTrading モード、監視閾値、PID ファイルパスなど）をプロパティ経由で取得可能に。
    - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェックなど）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 秘匿項目はマスク表示、選択肢・デフォルト提示、キャンセル時の安全な扱いなど。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DB パス親ディレクトリチェック、YAML の存在/パースチェック（PyYAML がない場合は警告）を実施。
    - `--strict` オプションで警告も失敗と扱うモードを提供。
    - live 環境向けの追加ガード（LINE 通知設定の未設定や Kill Switch の自動クリア設定に関する警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソートと候補選定 (select_candidates)。
    - 等配分 (calc_equal_weights) とスコア加重配分 (calc_score_weights) を実装。全スコアが 0 の場合は等配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)：既存保有をもとにセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear → 1.0/0.7/0.3、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - ポジション数決定ロジック (calc_position_sizes) を実装。
    - allocation_method に `risk_based`, `equal`, `score` をサポート。lot_size 単位で切り上げ/切り捨て、単銘柄上限 (max_position_pct)、合計投入上限 (available_cash/max_utilization) を考慮。
    - aggregate cap 超過時にスケールダウンし、端数は lot 単位で残差の大きい順に追加配分するアルゴリズムを実装。
    - cost_buffer により手数料・スリッページ分を保守的に見積り可能。
    - 価格欠損時のスキップやログ出力等の堅牢性対策。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的ロギング初期化関数 setup_logging を提供。標準出力（stdout）出力と日次ローテートファイル出力（TimedRotatingFileHandler）を併用。
    - ログディレクトリ自動作成、環境変数/引数での LOG_LEVEL / LOG_DIR 解決、既存ハンドラのクリーンアップ、ファイルハンドラ作成失敗時のフォールバック（stdout のみ）を実装。
    - 日次ローテーションで 30 日分バックアップ保持。
  - utils/process_priority.py
    - Windows / POSIX (Linux, macOS, FreeBSD) を抽象化したプロセス優先度設定 set_process_priority と CPU affinity 設定 set_cpu_affinity を実装。
    - 権限不足や未対応 OS では警告を出して安全にスキップする挙動。
  - utils パッケージの初期化。

- モニタリング DB 初期化ユーティリティ
  - monitoring/monitoring_db.py への参照（init_monitoring_db）を用いて、監視テーブルの確保を起動時に行う（冪等）。

- Tools
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - データソースは paper_trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプション）。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）等を集計してレポート出力。
    - P95 計算、日付フィルタ、閾値による PASS/FAIL 判定を実装。デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）を設定。

- Research
  - research/factor_research.py（モジュール骨格）
    - DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）を意図した設計を追加。モメンタム計算関数 calc_momentum の雛形を開始（実装途中）。

### Changed
- ログ出力ポリシー
  - すべての起動スクリプトで setup_logging を最初に呼ぶように統一。コンソールは stdout を使う設計に変更（cron 等で stdout/stderr をリダイレクトする運用を想定）。

- DB 使用方針
  - 監視系（monitoring）は環境に関係なく本番の sqlite_path を参照する方針を明記。
  - 実行系（execution）は paper_trading 時に専用の paper_sqlite_path を参照し、本番 DB と分離する設計に変更（安全策）。

- process_priority の扱い
  - 起動直後にプロセス優先度を高に設定するフローを採用。権限がない場合は警告ログを出して処理を継続。

### Fixed
- 環境変数のパース・読み込みに関する細かな不整合を修正
  - .env パーサがクォート内のエスケープやインラインコメントを正しく扱うよう改善。
  - 自動ロード時に OS 環境変数を上書きしない保護機構を追加（protected set）。

- run_monitoring のポーリング間隔取り扱い
  - MONITOR_POLL_INTERVAL が不正（非整数・0 以下）の場合に ValueError でクラッシュしないように、警告ログを出してデフォルト値へフォールバックするよう修正。

- 設定検証の堅牢化
  - validate_config.py で PyYAML 未導入時に YAML 検証をスキップして警告するように変更し、YAML 未存在時にも明示的な警告を出すように改善。

### Notes
- 一部モジュール（research.calc_momentum 等）は実装途中または骨組みの段階です。将来的に DuckDB クエリやファクター算出ロジックを追加していく予定です。
- .env ファイルは秘匿情報を含むため、絶対に VCS にコミットしないことを README 等で強く推奨します（config_setup.py のヘッダにもその旨を記載）。
- paper_trading と live の DB 分離、kill/stop フラグによる運用制御、ログローテーション等は運用上の安全性を向上させるための設計です。導入時は validate_config で設定を検証してください。

---

参照:
- 実装ファイル群: src/kabusys/*.py（config, config_setup, validate_config, run_execution, run_monitoring, portfolio/*, utils/*, tools/*, research/*）