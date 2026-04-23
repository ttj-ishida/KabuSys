# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に従っています。  

- リリース方針: 重大な変更は Breaking Change として明確に記載します。  
- フォーマット: https://keepachangelog.com/ja/ に準拠。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージとバージョン情報
  - pakcage バージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルの存在で検出。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - 例外発生時のログ出力とループ継続処理を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時・実行中に data/stop_requested.flag を確認して安全停止。
    - 実行用 PID ファイルを data/execution.pid に出力することを想定。

- 設定管理・ウィザード・検証
  - config.Settings クラス: 環境変数をラップしてアプリ設定を提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のデフォルトを持つ。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。
  - config_setup: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu API 等の必須項目とログ設定、Kill Switch 関連を対話的に設定可能。
    - 既存 .env 読み込み・更新、秘密値は表示をマスク。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` による警告の失敗扱いが可能。

- Portfolio モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に基づく配分（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく乗数を返す（未知レジームはフォールバックして 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・ポートフォリオ指標から発注株数を計算（risk_based / equal / score の方式、単元株丸め、aggregate cap スケーリング、cost_buffer の考慮など）。

- ユーティリティ
  - utils.logging_setup: 標準化されたログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ自動作成、既存ハンドラの重複防止対策。
    - 環境変数 LOG_LEVEL、LOG_DIR によるオーバーライド。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応。アクセス権限や未対応 OS は警告を出してスキップ。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率(send rate)、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定（閾値はソース内に定義）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。

- research モジュール（途中まで実装）
  - research.factor_research: DuckDB を利用したファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボラティリティ等の計算方針を実装予定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計。

- DB 初期化/監視関連
  - monitoring.monitoring_db.init_monitoring_db を通じて監視用テーブルの冪等な初期化を行うフローを run_*.py で呼び出すように統一。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （現時点で特記事項なし）

---

注記・設計上の意図・既知の留意点:
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行う。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings は未設定の必須環境変数に対して ValueError を送出します。validate_config CLI で事前チェックすることを推奨します。
- run_execution はペーパートレード時に本番 DB と完全分離する設計ですが、paper_fill_mode や PAPER_TRADING_SQLITE_PATH の設定により挙動が変わります。
- portfolio モジュールは「純粋関数」として設計されており、ユニットテストが容易です。将来的に単元株（lot_size）の銘柄ごとの差異を反映する拡張を予定しています。
- process_priority / cpu_affinity の設定はプラットフォームと実行権限に依存するため、失敗時は警告ログを出してスキップする実装です。
- Paper Verification レポートは既定の閾値をソース内で定義しています。運用に合わせて閾値や判定基準を調整してください。

今後の予定（例）
- factor_research の完成（各ファクター計算の SQL 実装完了・正規化）
- strategy / execution 部分の詳細実装・ユニットテスト強化
- CI ワークフローで validate_config / linters / type checks の自動化

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は必要に応じて修正・追記してください。）