# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-21

初回リリース。

### Added
- パッケージの基本構成を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行スクリプト / サービス
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を使用）。
    - monitoring は環境にかかわらず本番用 sqlite パスを使用して DB 初期化（`init_monitoring_db`）。
    - DuckDB 接続を併用。

  - run_execution:
    - ExecutionEngine 起動スクリプトを提供。
    - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカー（Paper Trading）用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 起動前に停止フラグ（data/stop_requested.flag）が立っている場合は起動せず終了。
    - 実行中は停止フラグ検知でエンジンを安全停止。`data/execution.pid` を PID ファイルとして使用。
    - ブローカー、OrderRepository、OrderManager、RiskManager（デフォルト設定を含む）、Reconciler、ExecutionEngine の組み立てロジックを実装。

- 設定管理
  - config:
    - .env 自動ロード機能を提供（プロジェクトルートを .git または pyproject.toml から検出）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト向け）。
    - .env パーサーで以下に対応:
      - `export KEY=val` 形式のサポート
      - シングル/ダブルクォート内のバックスラッシュエスケープの解釈
      - クォートなしの場合のインラインコメント認識（`#` の前が空白/タブならコメント）
    - Settings クラスを提供し、環境変数に対する便利なプロパティを公開（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, `cpu_threshold_pct` 等）。
    - `paper_fill_mode`（Paper Trading の約定挙動）に対するバリデーション（有効値: "instant","partial","never","reject"）。
    - `env` / `is_live` / `is_paper` / `is_dev` の判定ロジックと LOG_LEVEL バリデーション。

- 設定ツール / 検証ツール
  - config_setup:
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - J-Quants / kabu ステーション / DB / LINE / ログレベル / Kill Switch 関係など主要項目を対話的に設定可能。
    - シークレット項目はマスク表示、保存前の確認プロンプトあり。
    - .env のテンプレートヘッダと注意書き（Git にコミットしない等）を含めて出力。

  - validate_config:
    - .env および config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）の存在チェックとプレースホルダ値検出。
    - `KABUSYS_ENV`、`LOG_LEVEL`、DB パスの親ディレクトリ確認（存在しない場合は警告）。
    - PyYAML がインストールされている場合は config/*.yaml のパース検証を実施。
    - `KABUSYS_ENV=live` のときは本番向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を警告。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレークに signal_rank を使用する銘柄選定。
    - calc_equal_weights / calc_score_weights: 等配分 / スコア加重（合計スコアが 0 の場合は等配分にフォールバック、警告出力）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull":1.0、"neutral":0.7、"bear":0.3）。未知レジームは 1.0 にフォールバック（警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、全体投下キャップ（max_utilization）を考慮。
    - cost_buffer による保守的コスト見積りを導入し、必要時はスケールダウン（remaining_cash を使い fractional 残差の基で lot 単位で追加配分）。
    - 価格欠損時はスキップしてログ出力。

- ユーティリティ
  - utils.logging_setup:
    - 一貫したロギング設定関数 `setup_logging(app_name, log_dir, level)` を提供。
    - StreamHandler を stdout に設定（cron/Task Scheduler 対応）、TimedRotatingFileHandler による日次ローテーション（30日保持）。
    - LOG_DIR（環境変数）や引数でログ出力先を制御可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作継続。

  - utils.process_priority:
    - `set_process_priority(level)` でプラットフォーム差分を吸収してプロセス優先度を設定（Windows/Linux/macOS で対応）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアにプロセスを固定するユーティリティ。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- 解析 / レポートツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）から検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルトの合格基準（しきい値）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 集計期間はコマンドライン引数 `--from` / `--to` で指定可能。`--db` で DB パスを上書き可能。
    - データ欠損やテーブル未存在時は適切に N/A を表示し FAIL 条件を報告。

- 研究・ファクター計算（基礎実装）
  - research.factor_research:
    - ファクター計算モジュールのスケルトン（モメンタム、MA200、ATR、流動性等の定義と定数）。（calc_momentum の開始部分を含む。以降実装継続予定）

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Notes / Migration / Usage
- 環境変数周り:
  - 自動 .env 読み込みはデフォルトで有効。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - `.env` のパースはクォートやエスケープ、`export` プレフィックス、インラインコメント等に柔軟に対応します。
  - 主要な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development / paper_trading / live）
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - LOG_LEVEL, LOG_DIR
    - MONITOR_POLL_INTERVAL（run_monitoring の秒数）
    - PAPER_FILL_MODE（paper_trading の約定モード: instant/partial/never/reject）
    - KILL_FLAG_CLEAR_ON_START（本番環境ではデフォルト 0 を推奨）

- 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

- Safety:
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、権限不足や未対応 OS の場合は警告を出して継続します。
  - 停止フラグファイルや PID ファイルを使った安全停止・状態管理を想定しています。運用時は data ディレクトリのパーミッションとフラグ管理に注意してください。

今後の予定:
- research.factor_research の完全実装。
- 戦略/発注周りの単体テストと追加の検証ツール。
- BrokerClient の具体実装（本番 / モック）周りの拡張とテスト。