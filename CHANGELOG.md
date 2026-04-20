# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

なお、本ファイルはコードベースからの推測に基づく変更説明です。実際のコミット履歴や PR の説明に基づくものではありません。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期リリース。パッケージ名: KabuSys（日本株自動売買システム）。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視し、検知で安全にループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - SQLite / DuckDB 接続を初期化し、SystemMonitor.check_once() を定期実行。
    - KeyboardInterrupt を捕捉して正常終了。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient / paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で engine.stop() を呼びエンジンを停止。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env ファイルの自動ロード（プロジェクトルート検出）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の環境変数をラップ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
    - env/log level のバリデーション、有用なデフォルト値を提供。
    - kill/ pid /監視閾値など監視関連設定を提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。

- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で主要環境変数を設定し .env を生成。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用に対応。
  - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml 存在と YAML パースチェック（PyYAML がインストールされている場合）。
    - --strict オプションで警告も失敗扱いにできる。

- ツール
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL を判定する。
    - デフォルト DB パスは data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで上書き可能。
    - P95 計算、期間フィルタ（--from / --to）に対応。DB 不存在時のエラーメッセージ出力。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順（同点は signal_rank 昇順）で候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限。既存保有のセクター比率が閾値を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバック 1.0。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（スリッページ・手数料見積り）を考慮した調整ロジック。
    - リスクベース配分（risk_pct, stop_loss_pct）に対応。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラのクリア処理、ログディレクトリの自動作成、作成失敗時のフォールバック（ファイル出力無効化）を実装。
    - LOG_LEVEL / LOG_DIR / 引数 level / log_dir による解決順を備える。
  - utils/process_priority: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux / Darwin / FreeBSD）を吸収する実装。
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告を出してスキップ。

- リサーチ
  - research/factor_research（モジュール追加、モメンタムなどのファクター計算の骨組みを実装中）。
    - モメンタム計算の仕様（1M/3M/6M リターン、MA200 乖離等）をコメントで明示。DuckDB 接続を受ける設計。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Security
- なし

### Notes / Implementation details（補足）
- .env ファイルの読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しない。
- .env パーサはクォート（シングル/ダブル）内のバックスラッシュエスケープや、インラインコメントの扱い（クォート有り/無しでの差）に対応している。
- ログの StreamHandler は stdout を使う（cron 等で stdout/stderr を一本化したい運用を想定）。
- run_monitoring は環境に関係なく本番用 sqlite_path を利用する設計（監視データは一元管理する意図）。
- run_execution は paper_trading 環境を完全に分離（専用 SQLite）し、paper トレードの痕跡が本番 DB に混入しないよう配慮している。
- validate_config は PyYAML が未インストールでも graceful に動作し、その場合は YAML 検証をスキップする。

---

開発中のモジュールや未実装部分（例: research/factor_research の実装途中や将来的な拡張点）はコード内コメントとして記載されています。今後のリリースでは各モジュールの完全実装、テスト追加、ドキュメント拡充などが期待されます。