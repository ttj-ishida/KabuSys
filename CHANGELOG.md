# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測した変更点・機能一覧を基に作成されています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19
最初の公開リリース（推定）。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築・リスク管理・ポジションサイジング論理、調査（ファクター）部、開発支援ツールなどを収録。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - PID ファイル書き込みや停止フラグ（data/stop_requested.flag）での安全停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグでループを安全に終了し、例外発生時もログを残して次回ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）。
    - .env のパースは export 形式、クォート付き値、エスケープ、インラインコメントなどに対応。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading 用設定、監視閾値、PID/kill flag パス等）を提供し、値検証を実施（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の検証）。
    - Settings クラスと settings シングルトンを公開。

  - config_setup.py
    - .env を対話式に生成・更新するウィザード CLI を追加。既存値の読み込み、シークレット扱い、保存確認、デフォルト値提示などを実装。

  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML 利用可の場合）などを行い、errors/warnings/infos を出力。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全零時は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有時価を元にセクター曝露が閾値を超える場合に候補を除外）。
    - レジーム乘数 calc_regime_multiplier（bull/neutral/bear に応じる乗数、未知レジームは警告して 1.0 をフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes（allocation_method="risk_based" / "equal"/"score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ見積）反映、残余配分ロジックなどを備える。

- 監視・分析用 DB 統合
  - 監視テーブル初期化 util（monitoring.monitoring_db を参照して init_monitoring_db を使用）を run_* スクリプトで呼び出し、監視テーブルの存在を保証。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ初期化関数 setup_logging を追加。stdout への StreamHandler と日次ローテーション FileHandler（TimedRotatingFileHandler、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL/アプリ名指定に対応。ログディレクトリ作成失敗時はファイル出力を無効化。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度・CPU affinity を設定するユーティリティを追加。psutil を用い、権限不足時は警告してスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）からレポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を表示。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - Momentum 等のファクター計算（momentum, MA200 乖離、ATR、流動性等）を行う関数 calc_momentum などの骨格を実装（DuckDB 接続を受け取り SQL/Python で計算する設計）。（ファイル末尾に続きあり）

### Changed
- 設計上の分離
  - Paper Trading と Live の DB/挙動を明確に分離（Execution 起動時に settings.is_paper を参照して paper_sqlite_path を使用）。
- ログ出力の一元化
  - 全起動スクリプトから setup_logging を呼び出す想定でログ設定を統一。

### Fixed
- 環境変数ロードの堅牢化
  - .env の export 形式、クォート・エスケープ、インラインコメント対応により多様な .env フォーマットを正しく読み込み。

### Security
- シークレット扱い項目の対話式マスク
  - config_setup の対話で J-Quants / kabu API のシークレットはマスク表示。

### Notes / Known limitations
- 一部関数は TODO コメントや将来的な拡張（銘柄ごとの lot_size マスタ、前日終値フォールバックなど）を含む。
- research/factor_research.py はファイル末尾に続きがある（本 changelog 作成時点では一部が未表示）。
- 一部環境では psutil による優先度変更や cpu_affinity が権限不足で失敗する可能性があり、その場合はログに警告を出してスキップします。
- .env の自動ロードはプロジェクトルートが見つからない場合または環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定された場合にスキップされます。

---

参照:
- パッケージバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0"（本 CHANGELOG のベース）