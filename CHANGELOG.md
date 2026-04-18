# Changelog

すべての非互換性のある変更は明記します。  
このファイルは Keep a Changelog の形式に準拠しています。  
参照バージョン: __version__ = 0.1.0

※ 本 CHANGELOG は提示されたコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本機能: KabuSys 初期リリース（バージョン 0.1.0）。日本株自動売買システムの基盤モジュールを追加。
- 実行スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動し、プロセス優先度設定・停止フラグ監視・PID ファイル管理を行う。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離。
    - 起動時に監視テーブルの作成を保証する init_monitoring_db を実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は実行環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用してデータを記録。
    - stop_requested.flag を検知して安全にループ終了。
- 設定関連:
  - config.py
    - .env ファイルと環境変数を扱う Settings クラスを追加。多くの設定（DB パス、API トークン、モード判定、閾値など）を環境変数経由で取得。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。ロード順序は OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パースは export プレフィックス、クォート（エスケープ含む）、インラインコメント等に対応する堅牢な実装。
    - 設定検証（値域チェック）: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェック。is_live/is_paper 等の補助プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の読み込み、シークレット項目のマスク表示、確認後の保存を実装。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。PyYAML がない場合は YAML 検証をスキップして警告を出す。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等金額配分へフォールバックし警告を出す。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用して新規候補をフィルタするロジックを実装（売却予定銘柄の除外、"unknown" セクターは制限の対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告を出す）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数算出。単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、コストバッファの考慮、残差分配ロジック等を実装。
- ユーティリティ:
  - utils.process_priority
    - set_process_priority(level) を追加: Windows / POSIX 両対応（psutil 使用）。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加: 指定コアにプロセスをピン留め。例外発生時は警告を出してスキップ。
- リサーチ / ファクター計算:
  - research.factor_research
    - DuckDB 接続を用いたファクター計算モジュールを追加。モメンタム（1M/3M/6M、MA200 乖離）／ボラティリティ（ATR20、相対 ATR、出来高関連）などを計算する関数を提供。prices_daily テーブルのみ参照し外部 API に依存しない設計。
- ツール:
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定する。閾値はソース内で定義されている（例: uptime >= 99.0% 等）。--from/--to/--db オプションに対応。
- パッケージ初期化:
  - kabusys/__init__.py にバージョンと主要サブパッケージ一覧を追加。

### Changed
- ロギング/起動時のデフォルト挙動:
  - 実行スクリプト（run_execution/run_monitoring）は main() 内で logging.basicConfig(level=logging.INFO) を設定して簡易なログ出力を行う。
- DB 初期化:
  - run_execution と run_monitoring 起動時に init_monitoring_db(sqlite_conn) を呼び出し、監視用テーブルが存在することを冪等的に保証するようにした。

### Fixed / Robustness
- .env パーサ:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定など様々な形式に対応することで、.env の読み込みを堅牢化。
- 環境変数のデフォルト/検証:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対してデフォルトへフォールバックし、警告を出すように変更。
  - PAPER_FILL_MODE 等の列挙型環境変数は不正値でエラーを出すことで設定ミスを早期発見できるようにした。
- ExecutionEngine 停止制御:
  - 外部の停止フラグ（data/stop_requested.flag）を監視し、検知時に安全に停止処理を行う設計を採用。
- DuckDB / SQLite の接続管理:
  - 各スクリプトで起動時に接続を張り、終了時に確実に close() することでリソースリークを防止。

### Documentation / CLI help
- 各 CLI スクリプトに docstring と簡易な使用例を追加（モジュールの先頭に使用方法の記載あり）。validate_config と config_setup はコマンドライン引数（--strict, --env-file 等）をサポート。

### Notes / Known limitations
- process_priority/set_cpu_affinity: 実行環境によっては権限不足で設定に失敗する可能性があり、その場合は警告を出してスキップする動作になっている。
- portfolio.position_sizing:
  - price が欠損（0.0）の場合の扱いに TODO コメントあり（現在はスキップ）。
  - lot_size は現時点で全銘柄共通固定。将来的に銘柄別単元対応を検討。
- config.auto-load:
  - プロジェクトルート検出が失敗した場合は自動 .env ロードをスキップするため、配布後や一部環境で手動で環境変数を設定する必要がある場合がある。
- Paper trading と本番 DB 間は明示的に分離される設計だが、運用者は環境変数（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を適切に設定すること。

---

この CHANGELOG はコードから推測した変更点・機能一覧をまとめたものであり、実際のコミット履歴と完全には一致しない可能性があります。追加の変更点や修正があれば、リリースノートを更新してください。