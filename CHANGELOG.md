# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
本リポジトリの初期リリースを記録しています。

全般:
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- リリース日: 2026-04-25

## [0.1.0] - 2026-04-25

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) の存在を監視し、安全にループを終了。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（data/paper_trading.db）で本番 DB と分離。
    - エンジン停止用の停止フラグと PID ファイル管理を実装（data/execution.pid）。
    - スレッドで実行し、停止フラグ検知時にエンジンを停止。

- 設定・検証・ウィザード
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
    - .env のパースロジックを実装（export 形式、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスを導入し、環境変数のアクセス・検証・デフォルト解決を提供（DB パス、PID パス、各種閾値、KABUSYS_ENV 等）。
    - 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 作成／更新ウィザードを追加。既存 .env 読み込み・シークレットマスク表示・保存機能を提供。
  - validate_config.py
    - 起動前チェック用 CLI を追加。.env および config/*.yaml の存在／基本妥当性チェックを行う。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分／スコア加重 (calc_equal_weights, calc_score_weights) を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数 calc_regime_multiplier を追加。
  - portfolio/position_sizing.py
    - 株数計算ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング等を実装。
  - portfolio/__init__.py で上記 API を公開。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout へ StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）を設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップ）。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。
  - utils/process_priority.py
    - プラットフォームに依存しないプロセス優先度設定（Windows の priority class、POSIX の nice 値対応）を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - アクセス権限不足等のケースは警告ログを出して安全にスキップ。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計を行い、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を算出する検証レポート生成スクリプトを追加。
    - PASS/FAIL 判定基準（稼働率、成功率、送信率、P95 レイテンシの閾値）を組み込み。
    - コマンドライン引数 --from / --to / --db に対応。

- 研究用モジュール
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を利用したファクター計算（Momentum / Value / Volatility / Liquidity）計画の骨子を追加（関数群の実装方針と定数を含む）。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_monitoring/run_execution 起動時に呼ぶことで監視用テーブルの存在を保証（冪等な初期化処理）。

### Changed
- ログの挙動・構成
  - logging_setup.setup_logging で既存のハンドラを一旦 flush/close してから再設定することで、複数回初期化した場合の二重出力を防止。
  - StreamHandler は stdout を用いる設計（cron/Task Scheduler でのリダイレクトを想定）。

- 起動時のプロセス優先度
  - 主要な起動スクリプト（monitoring / execution）で最初に set_process_priority("high") を呼び、プロセス優先度を高くする運用方針を採用。

- 設定ロードの優先順位
  - .env の自動読み込み順は OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない（.env.local は override=True で上書き可能だが OS 環境変数は保護）。

### Fixed
- 環境変数パースの堅牢性
  - MONITOR_POLL_INTERVAL が不正（整数化不可や 0 以下）の場合、警告を出してデフォルト値（60 秒）にフォールバックする処理を追加。
  - Settings.paper_fill_mode のバリデーションを追加し、不正な値は ValueError で早期検出。

- DB 初期化の安全化
  - run_execution でも init_monitoring_db を呼ぶことで、監視テーブルが存在しない環境でも起動時に必要テーブルを作成（冪等処理）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

補足 / 既知の制約・TODO
- research/factor_research.py は設計方針と定数、関数スケルトンが含まれており、一部実装が未完（ファイル末尾が途中で切れている可能性あり）。本リリースでは研究／検証用途の骨子提供に留まる。
- position_sizing.py / risk_adjustment.py にいくつかの TODO コメントあり（例: 価格欠損時のフォールバック戦略、将来的な lot_size の銘柄別対応など）。
- .env に機密情報を含むため、README 等で .env を絶対に Git にコミットしないよう注意を促す旨が config_setup のヘッダに記載済み。
- 実運用（KABUSYS_ENV=live）時は validate_config.py による事前検証の活用を強く推奨。特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値は本番では慎重に扱うこと。

もしリリースノートの文言を英語版で併記したい、あるいは差分（変更ごとのコミットログをベースに詳細化）を追記したい場合はお知らせください。