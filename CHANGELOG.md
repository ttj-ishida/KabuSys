# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースの内容から推測して作成した CHANGELOG です。

フォーマット:
- Unreleased: 現在進行中の変更（空の場合あり）
- バージョンは package の __version__ に合わせています（現行: 0.1.0）

## [Unreleased]
- 現在のコードベースに基づく未リリースの変更はありません。

## [0.1.0] - 2026-04-18
初期リリース — 日本株自動売買システム "KabuSys" の基礎機能を実装。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離してペーパートレードを行う。
    - MockBrokerClient を使用する実行パスに対応する設計（ファクトリ経由）。
    - 実行中の停止検知用フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う実装。
    - スレッドで engine.run_session を実行し、停止フラグ検知で安全に停止するループを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する（監視データは共通で管理）。
    - 停止フラグ検知でループを正常終了する仕組みを実装。
- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数から設定値を取得する API を提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のデフォルトを定義。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を行う。
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）およびログレベル検証を実装。
    - 自動 .env 読み込み機能を実装（プロジェクトルート検出, .env → .env.local の順で読み込み）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 設定支援ツール / バリデーション
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / Kill Switch 等の主要項目を対話的に設定・保存可能。
  - validate_config.py
    - 起動前に必須環境変数や config/*.yaml、パスの存在などを検証する CLI を実装。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/ ディレクトリ、30日分保持）を設定する共通ユーティリティ。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続するフォールバックを実装。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。権限不足等の失敗は警告でフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有のセクター別時価で上限を判定し、超過セクターの新規候補を除外。
    - "unknown" セクターはセクター上限の適用対象外にする挙動を明示。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based, equal, score）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、手数料/スリッページ見積り用 cost_buffer 考慮のロジックを実装。
    - risk_based 方式ではリスクベースの数量計算（risk_pct, stop_loss_pct）を提供。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト: data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を出力するレポート生成スクリプトを提供。
    - P95 計算、日付フィルタ、CLI 引数（--from / --to / --db）をサポート。
    - デフォルトの判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用ファクターモジュール（骨格）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等の計算方針を定義したモジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。処理の一部は実装中（ファイルは断片的に含まれる）。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- ログ出力方針
  - 標準出力は stdout を利用するよう統一（cron / Task Scheduler との相互運用を意識）。
  - 既存ハンドラがある場合は一度 flush/close してから再設定することで二重設定を回避。

### Fixed
- .env 読み込みの堅牢化
  - _parse_env_line にて export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント扱いのルールを実装し、より忠実に .env をパースするよう改善。

### Notes / Behavior
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず監視用 DB パス（Settings.sqlite_path）を使用する設計になっている点に注意。
- 実行 (run_execution) は paper_trading 環境では paper_sqlite_path を使用し DB を完全に分離する。これによりペーパートレードと本番データの分離が保たれる。
- process_priority.set_process_priority("high") が起動時に呼ばれ、可能な限り高優先度で起動を試みる（権限がない場合は警告でフォールバック）。
- validate_config により起動前チェックが可能。--strict を使うと警告も失敗扱いになり exit(1) を返す。
- ログディレクトリ作成に失敗した場合はファイルローテーションは無効化され、コンソールログのみで継続する。

### Known limitations / TODO
- research/factor_research.py はファイル末尾で途中（未完）となっている箇所があるため、ファクター計算の完全実装と単体テストを要する。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄毎の lot_map をサポートする予定）。
- apply_sector_cap における price が欠損 (0.0) の場合の取り扱いは注釈（TODO）あり。フォールバック価格（前日終値等）を導入することが推奨される。

---

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成したものです。実際のリリース履歴や日付・範囲は開発プロジェクトの運用実態に従って調整してください。