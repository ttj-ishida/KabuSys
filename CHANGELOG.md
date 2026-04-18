# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

## [0.1.0] - 初回リリース
リリース日: 未指定

### Added
- 全体
  - 初期リリース。KabuSys 自動売買システムのコアユーティリティ・CLI・ポートフォリオ構築・監視機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して graceful にループを終了。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は paper 用専用 SQLite（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動制御。
    - 停止フラグで実行中エンジンを停止する仕組みを備える。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・CLI
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数優先、`.env.local` を上書き読み込み。
    - 多数のプロパティ（DB パス、API トークン、監視閾値、環境判定 `is_live`/`is_paper`/`is_dev` 等）を提供。
    - `paper_fill_mode` の値検証を実装（有効値: "instant","partial","never","reject"）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成/更新。シークレット入力のマスク、選択肢・デフォルト値サポート、保存前確認あり。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース（PyYAML がある場合）などを検証。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - logging_setup: 統一的ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーをクリアしてから StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - `set_process_priority(level)` で Windows/Linux/Mac の差分を吸収して優先度を設定（権限不足や未対応 OS は警告してスキップ）。
    - `set_cpu_affinity(cpu_count)` でプロセスを最初の N コアにピン留め（権限不足時は警告してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: シグナルスコアでソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重（スコア合計が 0 の場合は等重にフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に対するデフォルト値と未知レジームのフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分に対応。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリングと残差配分）を実装。コストバッファ（手数料・スリッページ見積り）を考慮。
  - ポートフォリオ API のエクスポート（src/kabusys/portfolio/__init__.py）。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL を判定する。閾値はソース内定義で調整可能。
    - P95 計算、日時フィルタ、DB パス引数/環境変数サポートを実装。

- リサーチ（未完／着手）
  - factor_research（src/kabusys/research/factor_research.py）を追加（モメンタム等のファクター計算を実装予定）。モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials を参照して複数の定量ファクターを計算する設計。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- .env パーサの強化（src/kabusys/config.py）
  - export 構文、シングル／ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理などに対応。無効行をスキップする堅牢なパーシングを実装。
- run_monitoring の MONITOR_POLL_INTERVAL の検証を追加し、0 以下や不正値を検出した際にデフォルトへフォールバックして警告ログを出力するようにした。

### Security
- なし

### Notes / Operational tips
- ログ
  - デフォルトログディレクトリは `logs/`。アプリケーションごとに `<app_name>.log`（例: execution.log, monitoring.log）が作成され日次ローテーションされます。
  - コンソール出力は stdout を使用（cron 等との併用を想定）。
- DB
  - DuckDB: 分析用（`DUCKDB_PATH`, デフォルト `data/kabusys.duckdb`）。
  - SQLite: 監視用 `SQLITE_PATH`（デフォルト `data/monitoring.db`）。ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
- 停止制御
  - 起動スクリプトはプロジェクトルートの `data/stop_requested.flag`（または設定されたパス）を監視して安全に停止します。
- 本番注意点
  - `KABUSYS_ENV=live` の場合、validate_config は追加の警告チェック（LINE 設定の有無や Kill Switch の自動クリア設定）を行います。Kill Switch の自動クリア（`KILL_FLAG_CLEAR_ON_START=1`）は本番では危険なので注意してください。

もし特定のモジュール・関数について詳細な変更点（例: 引数仕様や返却値、例外動作など）を CHANGELOG に追記したい場合は、対象箇所を指定してください。