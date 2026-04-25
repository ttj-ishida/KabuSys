# Keep a Changelog
すべての注記は https://keepachangelog.com/ja/ に準拠しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-25
初回公開リリース。システム全体の起動スクリプト、設定管理、監視・実行ランナー、ポートフォリオ構築ユーティリティ、ユーティリティ群、および検証/レポート用ツールを含みます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグファイル (data/stop_requested.flag) を検知して安全にループ終了。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して初期化する（監視データを共通 DB に保持）。
    - 起動時にプロセス優先度を「high」に設定。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - エンジン用の PID ファイル管理、停止フラグ監視 (data/stop_requested.flag) による安全停止処理。
    - 起動時にプロセス優先度を「high」に設定。

- 設定管理
  - kabusys.config.Settings クラス
    - .env および環境変数から各種設定値を取得するユーティリティを追加。
    - 自動 .env ロード:
      - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み（OS 環境変数を保護）。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種プロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（PAPER_TRADING_SQLITE_PATH でペーパートレード DB 指定可）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU/MEMORY/DISK 閾値 (CPU_THRESHOLD_PCT 等)
      - KABUSYS_ENV（development|paper_trading|live）, LOG_LEVEL の検証
      - PAPER_FILL_MODE（instant|partial|never|reject）の検証

- 設定用 CLI / 検証ツール
  - config_setup.py
    - .env の対話式ウィザードを追加。項目の説明、シークレット入力、既存 .env の読み込み、保存機能を提供。
    - デフォルトや選択肢を提示し、最終確認後に .env を生成・更新する。
  - validate_config.py
    - 起動前に必須環境変数や一般的な設定ミスをチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML がある場合は）パース検証、本番時のガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を行う。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群、DB 未使用）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択、タイブレークは signal_rank。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存ポジションと価格からセクター別エクスポージャーを算出し、上限を超えるセクターの新規候補を除外。unknown セクターは上限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは警告のうえ 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。
      - risk_based: リスク許容率（risk_pct）とストップロス比率（stop_loss_pct）を用いた算出。
      - equal/score: weight に基づく配分。
      - 単元株（lot_size）丸め、1 銘柄の上限（max_position_pct）やポートフォリオ全体の利用上限（max_utilization）を考慮。
      - cost_buffer（手数料・スリッページ見積り）を加味して合計投資額が available_cash を超える場合はスケールダウンし、端数は lot_size 単位で再配分するロジックを実装。

- ユーティリティ
  - logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。既存ハンドラのクリアを行い二重設定を防止。
    - LOG_DIR または引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を提供（set_process_priority）。
    - CPU affinity 固定機能（set_cpu_affinity）を追加。
    - 権限不足や未対応環境では警告を出してスキップ。

- 監視 DB 初期化 / DuckDB
  - monitoring_db.init_monitoring_db（参照実装を使用）を run_monitoring/run_execution 起動時に呼び出し、必要な監視テーブルが存在することを保証（冪等）。
  - DuckDB 統合: duckdb パスを Settings で指定し、実行時に duckdb.connect を確立。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）から集計して検証レポートを標準出力に生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - デフォルト閾値: uptime >= 99.0%, fill_rate >= 90.0%, send_rate >= 95.0%, P95 latency <= 200 ms。
    - --from/--to オプションで期間指定可能。データ欠如時は N/A を表示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

補足（開発者向けメモ）
- .env のパーサはクォート内のバックスラッシュエスケープを考慮し、アンコメント処理の挙動も実装済み。export KEY=val 形式にも対応。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す設計（CI 環境では PyYAML を導入推奨）。
- 実行時は各 CLI をモジュールとして実行可能:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

バグ報告や改善提案は issue を立ててください。