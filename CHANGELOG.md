CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
バージョン 0.1.0 はパッケージ内の __version__ 値に合わせて初期リリースとしてまとめています。日付はコードの参照点（例: ドキュメント内の日付例）に合わせて設定しています。

フォーマットの簡単な説明:
- Added: 新規機能
- Changed: 既存機能の変更（後方互換性が破られている場合は明記）
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当があれば記載

Unreleased
----------

- 今後のリリースに向けた作業項目や修正点はここに記載します（現時点ではなし）。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション骨格を実装（初期リリース）。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用可能。
    - BrokerClientFactory を通して本番/モックブローカーの切替をサポート（KABUSYS_ENV に依存）。
    - ExecutionEngine をスレッドで実行し、 data/stop_requested.flag による安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority）。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - stop フラグ（data/stop_requested.flag）を検出してループを終了。
- 設定・ユーティリティ
  - config.Settings: 環境変数/ .env からの設定取得を集中管理する Settings クラスを追加。
    - 各種デフォルト値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）を提供。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、有効な値の制約を実装。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject、デフォルト: instant）。
    - is_live / is_paper / is_dev 等の便利プロパティ。
  - .env 自動ロード機構を実装:
    - プロジェクトルートを .git または pyproject.toml から探索し、.env/.env.local を自動で読み込む（必要に応じて上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
    - .env の簡易パーサはクォートやエスケープ、コメント処理に対応。
  - config_setup: 対話式ウィザードで .env を生成／更新する CLI を追加（python -m kabusys.config_setup）。
    - 項目一覧、デフォルト、シークレット項目のマスク表示等の対話サポート。
  - validate_config: 起動前に .env と config/*.yaml（存在する場合）の妥当性を検証する CLI を追加（--strict オプションあり）。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DBパスの親ディレクトリ確認、YAML パースチェック（PyYAML が存在する場合）等。
- ロギング
  - utils.logging_setup.setup_logging を追加。
    - stdout への StreamHandler と日次ローテートされたファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログ出力先は引数 / 環境変数 LOG_DIR / デフォルト logs/ の順で解決。
    - 既存ハンドラをクリーンに削除して二重設定を防止。
- プロセス管理ユーティリティ
  - utils.process_priority: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定関数を提供。
    - プラットフォーム差分を吸収し、権限不足等は警告ログでスキップ。
- データベース / 分析
  - DuckDB のサポート（Settings.duckdb_path、各スクリプトでの duckdb.connect）。
  - monitoring_db.init_monitoring_db を利用して監視テーブルの初期化（冪等）を担保。
- Portfolio モジュール（資産配分・サイズ決定）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 配分比率計算（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用するフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: weight / candidates / risk_based に応じて発注株数を決定。
    - 単元（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリングを実装。
    - 存在しない価格や単価 0 の場合はスキップして安全に処理。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）等を算出。
    - PASS/FAIL 判定基準を組み込み（稼働率 >= 99%、fill_rate >= 90% 等、ソース内で定義）。
    - コマンドラインで期間フィルタ（--from / --to）と DB パス指定（--db）に対応。
- research モジュール
  - research.factor_research: DuckDB を用いたファクター計算基盤（モメンタム、MA200乖離、ATR、流動性指標等）を追加（設計方針・定数を実装）。
    - prices_daily / raw_financials テーブルのみを参照して外部 API 非依存で計算する方針。

Changed
- なし（初回のまとまった追加のため変更履歴はなし）。

Fixed
- なし（初期実装のため既知のバグ修正履歴はなし）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / 実装上の注意点
- run_monitoring は「監視」用の DB パスとして Settings.sqlite_path（本番の monitoring.db）を参照します。環境にかかわらず本番監視用の DB に接続する設計になっているため、テスト等で分離したい場合は別途設定（環境変数の上書き等）を推奨します。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB と分離します。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や別ディレクトリでの実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます。
- process_priority / set_cpu_affinity は権限やプラットフォームによって動作しない場合があり、その場合は警告を出してスキップします。
- Portfolio の position_sizing 周りは lot_size（単元）を全銘柄共通で想定しているため、銘柄別単元対応は将来的な拡張予定（TODO コメントあり）。

今後の予定（例）
- factor_research の各ファクター計算を完成させる（ファイルは一部未完の可能性がある）。
- 単体テスト・統合テストの追加（特にポジションサイズ計算、スケーリングロジック、DB 初期化処理）。
- 銘柄別単元（lot_size）や手数料モデルの柔軟化。
- 監視・実行プロセスのより細かい運用監視・アラート連携（LINE 通知の拡張など）。

以上。必要であれば各コミット単位のより詳細な CHANGELOG（関数ごとの変更理由やサンプル出力例など）も生成できます。どの粒度で出力するか指示してください。