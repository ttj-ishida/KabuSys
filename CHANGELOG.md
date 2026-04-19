# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

全てのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知するとループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - SQLite / DuckDB の接続確立と監視 DB 初期化を実施。
    - check_once() 内の例外をログ出力して次回ポーリングへフォールバック。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を使用（data/paper_trading.db デフォルト）し Mock ブローカーを利用して本番 DB と分離。
    - 停止フラグ・PID ファイル制御に対応。ExecutionEngine を別スレッドで実行し、停止フラグで安全に停止可能。

- 環境設定・検証 CLI
  - config_setup.py
    - 対話式ウィザードにより .env の作成・更新を支援。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を用意。
  - validate_config.py
    - .env と config/*.yaml の起動前チェックを実装。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス・YAML ファイル存在チェック、live 環境向けガードを実施。
    - --strict オプションで警告も失敗扱いにできる。

- 環境変数ローダ
  - config.py
    - .env/.env.local の自動ロードを実装（OS 環境変数が優先）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の1行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - Settings クラスで各種設定値をプロパティとして提供（検証付き: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - paper_sqlite_path / sqlite_path / duckdb_path 等のデフォルトパスを提供。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を統一的に設定する関数 setup_logging を実装。
    - LOG_LEVEL / LOG_DIR / app_name に基づく柔軟な設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォームでは警告を出してフォールバック。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークは signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を超過しているセクターの新規候補を除外するロジックを提供（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）に丸め、1 銘柄上限・集約上限（available_cash）を考慮したスケーリング、cost_buffer（手数料/スリッページ見積）を加味した保守的見積り、残差処理による追加配分アルゴリズムを実装。

- 分析・研究モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を用いたファクター計算の設計とモメンタム指標等の定数・関数の骨格を追加（prices_daily / raw_financials テーブル参照を想定）。
    - P95 等統計計算や計算範囲バッファの考慮など設計済み。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH 指定可）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定（閾値はスクリプト内定義）。
    - 日付フィルタ（--from/--to）対応。DB のテーブル欠損時は個別にロバストにハンドリング。

### Changed
- なし（初回リリースのため比較対象なし）

### Fixed
- なし（初回リリース）

### Notes / Design decisions
- ポートフォリオ関連モジュールは「純粋関数」を志向し、DB や外部 API に依存しない設計。ユニットテストが容易。
- .env 自動ロードはプロジェクトルート検出（.git または pyproject.toml）を起点とし、カレント作業ディレクトリに依存しないように実装。
- run_monitoring は監視用 DB に対して環境に依存しない（常に sqlite_path）運用を想定し、監視側の独立性を確保。
- run_execution は paper_trading と live を明確に分離し、紙上検証と本番操作が混在しないよう配慮。
- ロギングは stdout を基準にしつつファイル出力を行う設計で、cron / systemd 等からの起動時の取り扱いを考慮。

もし詳細（各関数の仕様や追加してほしいリリースノート項目）が必要であれば、特定のファイル/機能ごとにより詳しい説明を作成します。