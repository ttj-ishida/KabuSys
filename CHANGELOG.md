# Keep a Changelog — CHANGELOG.md（日本語）
すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載します。

全般的な注意：
- リリース内容はコードベースから推測して記載しています。
- 初期リリースとしてバージョン 0.1.0 を記録しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期公開リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。

- CLI / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite DB を使用し、MockBrokerClient を利用することで本番 DB と完全に分離（環境に応じた DB 切替）。
    - 実行中の停止はプロジェクトルート/data/stop_requested.flag を監視して行う。
    - 起動時にプロセス優先度を "high" に設定する挙動を採用。
    - 実行 PID を data/execution.pid に保存する仕組みを使用（Engine に PID ファイルを渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告を出力する。
    - Monitoring は environment にかかわらず本番（settings.sqlite_path）を使用する旨の注記。
    - 停止はプロジェクトルート/data/stop_requested.flag を検知して正常終了。
  - kabusys.validate_config
    - .env と config/*.yaml の事前検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース検証（PyYAML がある場合）などを実施。
    - --strict オプションにより警告を FAIL 扱いにできる。
  - kabusys.config_setup
    - 対話式 .env ウィザードを追加。.env の初期作成／更新を支援。
    - J-Quants / kabu API など必須項目、LOG_LEVEL、DB パス、Kill Switch の設定項目をサポート。
    - 既存 .env の読み込み / Enter で既存値を再利用可能。書き込み時には .env に注意を促すヘッダを出力。
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して評価（基準閾値で PASS/FAIL 判定）。
    - --from / --to / --db オプションをサポート。環境変数 PAPER_TRADING_SQLITE_PATH を尊重。
    - P95 計算、NULL 安全なクエリ・例外処理を実装。

- 設定 / 環境周り
  - kabusys.config
    - 環境変数 / .env の自動ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml を探索）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env/.env.local の読み込みロジック（上書きポリシー、OS 環境変数保護）を実装。
    - 各種設定項目を Settings クラスとして提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須チェックは _require() で実施）。
    - デフォルト DB パス: DuckDB は `data/kabusys.duckdb`、SQLite（監視用）は `data/monitoring.db`、Paper Trading 用は `data/paper_trading.db`。
    - PAPER_FILL_MODE に対する入力検証（有効値: instant|partial|never|reject）。
    - kill/ pid ファイルパス、監視しきい値（CPU/MEM/DISK）等の設定項目を定義。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights / calc_score_weights）を追加。
    - score がすべて 0 の場合に等重配分へフォールバックする警告を実装。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有と当日売却予定の扱い、"unknown" セクターは除外しない等のロジックを実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知レジームはフォールバックして 1.0）。
  - kabusys.portfolio.position_sizing
    - ポジションサイズ計算 calc_position_sizes を追加。allocation_method（risk_based / equal / score）に対応し、lot_size の丸め、単銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
    - risk_based では risk_pct / stop_loss_pct を用いた算出、equal/score では重みから算出。

- モニタリング / DB 初期化
  - monitoring.monitoring_db への初期化呼び出し（init_monitoring_db）を run_execution と run_monitoring の起動時に統合（テーブル存在を保証、冪等）。

- ユーティリティ
  - kabusys.utils.logging_setup
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順とハンドラ二重設定防止ロジックを実装。
  - kabusys.utils.process_priority
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する機能を追加。psutil を用いて nice / priority class を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足等で設定失敗した場合は警告を出してスキップ。

- リサーチ（下地）
  - kabusys.research.factor_research
    - DuckDB を用いたファクター計算モジュールの追加（モメンタム / MA200 / ATR / Value / Liquidity 等の算出を想定）。calc_momentum の初期実装を含む（ファイル末尾で実装途中の可能性あり）。

### Changed
- 既存配布物がないため「変更」は特になし（初期リリース）。

### Fixed
- 初期リリースのため「修正」は特になし。

### Deprecated
- なし。

### Removed
- なし。

### Security
- .env ファイルは機密情報を含むため絶対に Git にコミットしない旨を config_setup の生成ヘッダに明記。
- Settings._require により必須環境変数未設定時は ValueError を送出するため、CI/運用での環境変数管理を推奨。

### Notes / 注意事項
- run_monitoring の実装は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」とコメントに記載されているため、開発時に意図しない DB 更新が行われないよう注意してください。
- run_execution は paper_trading 環境で専用 DB（PAPER_TRADING_SQLITE_PATH）を使用する設計だが、Settings の env の設定ミスが本番寄りの動作を引き起こす可能性があるため、kabusys.validate_config で事前チェックすることを推奨します。
- process_priority / cpu_affinity の設定は権限や OS に依存するため、失敗した場合は警告が出力されるのみで起動自体は継続します。
- kabusys.research.factor_research は DuckDB のテーブル（prices_daily, raw_financials 等）を前提としており、環境整備が必要です。

---

（以降のリリースでは「Added」「Changed」「Fixed」等で差分を追記してください。）