# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。
 semantic versioning を想定しています。

現在のリリース
----------------

### [0.1.0] - 2026-04-22

Added
- 初期リリース: KabuSys の基本機能を追加
  - 環境 / 設定
    - Settings クラスを導入し、環境変数経由で各種設定を参照可能に（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
    - .env 自動読み込み実装（プロジェクトルートの .env, .env.local を OS 環境変数を保護しつつ読み込み）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの強化: export 形式のサポート、クォート内のエスケープ処理、インラインコメント処理など。
    - Settings に多数のプロパティを追加（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID ファイル / Kill フラグ関連 / CPU/MEM/DISK 閾値 / PAPER_FILL_MODE のバリデーション など）。
  - 設定ワークフロー
    - 対話式環境設定ウィザード（kabusys.config_setup）を追加。`.env` の初期作成・更新を支援。
    - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数や config/*.yaml の存在・パースをチェック。`--strict` で警告を失敗扱いにできる。
  - 実行 / 監視
    - 実行エントリスクリプト: run_execution（ExecutionEngine の起動スクリプト）を追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
      - BrokerClientFactory により環境に応じたブローカークライアントを生成（モックが利用される想定）。
      - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による安全停止に対応。
      - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
      - 監視テーブル初期化 (init_monitoring_db) を呼び出して冪等に監視テーブルを確保。
    - 監視エントリスクリプト: run_monitoring を追加。
      - SystemMonitor を用いたポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト: 60 秒）。不正な値時はデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
      - 停止フラグ / PID ファイルの利用、例外キャッチしてログ出力後に次ポーリング継続。
  - ロギング / 実行環境
    - logging_setup ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリの解決優先度や失敗時のフォールバック処理を実装。
    - process_priority ユーティリティを追加。Windows / POSIX を透過してプロセス優先度（nice/HIGH_PRIORITY_CLASS 等）を設定。CPU affinity（最初 N コアに固定）もサポート。権限不足や未対応環境では警告を出してスキップ。
  - ポートフォリオ構築（純関数群）
    - portfolio モジュールを追加:
      - portfolio_builder: select_candidates（スコア降順で上位選定）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分配へフォールバック）。
      - risk_adjustment: apply_sector_cap（セクター上限チェックで候補除外）、calc_regime_multiplier（regime に応じた資金乗数; bull/neutral/bear のマップ、未知はフォールバック）。
      - position_sizing: calc_position_sizes（risk_based / equal / score の allocation_method に対応、lot_size 単位への丸め、per-position / aggregate cap、cost_buffer を考慮したスケールダウンと端数処理）。
  - 解析 / レポート
    - tools/paper_verification_report を追加。paper_trading 用 SQLite から指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ統計）を集計し、閾値に基づく PASS/FAIL 判定を行う CLI。
      - P95 計算、期間フィルタ（ISO8601 UTC）対応、DB 存在チェック、出力フォーマットを備える。
  - 研究用モジュール（開始）
    - research/factor_research の骨組みを追加（DuckDB を使ったファクター計算設計、モメンタム / Value / Volatility / Liquidity ファクターの方針、calc_momentum の実装開始）。

Changed
- 環境変数の取り扱い
  - .env の読み込み順序を明確化（OS 環境 > .env.local > .env）。OS の既存環境変数は保護され、.env.local による上書きは可能だが保護対象キーは上書かない。
- ロギング
  - stdout を標準出力先に選択（stderr ではなく）することで cron / Task Scheduler 等での出力リダイレクトを想定。
- DB
  - run_execution は paper_trading の場合に paper_sqlite_path を使用することで本番監視 DB と分離。run_monitoring は常に sqlite_path（本番監視 DB）へ接続する仕様。

Fixed
- .env パーサーの堅牢化
  - export 付き行、クォート内のエスケープ、インラインコメントの扱い等を改善し、ユーザーの .env 設定ミスに耐性を持たせた。
- 各種フォールバックと明示的なログ出力
  - 設定値が無効な場合にデフォルトへフォールバックし、警告ログを出す実装を追加（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL 等）。

Security
- .env 取り扱いに注意喚起を追加（config_setup が生成する .env に対して Git へのコミット禁止を明記）。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須（validate_config がチェックを行う）。
- paper_trading を使う場合:
  - KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を利用。paper_trading は本番 DB と分離される設計。
- 起動および停止:
  - 実行中の停止はプロジェクトルート/data/stop_requested.flag にファイルを作成することで行える（run_execution / run_monitoring が検知して終了処理を行う）。
- ログ:
  - デフォルトログディレクトリは logs/。外部で変更する場合は環境変数 LOG_DIR または setup_logging の引数を利用。

開発中 / TODO（本文中の注記）
- position_sizing の price フォールバック（price が欠損する場合の扱い）をより堅牢にする予定。現在は 0.0 を使うため過少見積りになる可能性あり。
- research/factor_research の実装継続（calc_momentum の続き等）。

Unreleased
- なし（初回リリース）

--------------------------------
この CHANGELOG はコードベースからの推測に基づいて作成しています。実際の変更履歴やリリース日付はプロジェクトの運用ポリシーに合わせて調整してください。