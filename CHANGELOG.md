# Changelog

すべての notable な変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

全般的な注記
- 本リリースはパッケージバージョン 0.1.0 に対応します（src/kabusys/__init__.py の __version__ を参照）。
- 多くのモジュールは CLI スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ群、検証/レポートツールを含みます。

## [0.1.0] - 2026-04-19

### Added
- 起動用スクリプトを追加/提供
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して実行可能。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）の取り扱いを実装。
    - プロセス優先度を "high" に設定して起動する仕組みを導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt に対する安全終了処理を実装。
- 設定管理/初期化機能
  - config.py
    - Settings クラスでアプリケーション設定を集中管理。
    - .env ファイルの自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可。
    - .env の行パーサーは export プレフィックス、引用符（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。
    - 各種環境変数のアクセサプロパティ（J-Quants、kabu API、DB パス、Paper Trading モード、監視閾値、ログレベル等）を提供。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - 秘匿値のマスク表示、選択肢サポート、既存 .env の読み込みと再利用、.env 書き込みロジックを実装。
- 設定検証 CLI
  - validate_config.py
    - .env や config/*.yaml の存在や妥当性をチェックする CLI。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config ファイルの存在確認、live 環境向けの追加ガードなどを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ログ/プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテートする TimedRotatingFileHandler をルートロガーへ設定（ログ保存ディレクトリは引数/環境変数/デフォルトで解決）。
    - 既存ハンドラをクリアして二重出力を防止。ログファイル作成に失敗した場合はコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、許可エラー等は警告ログでスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py
    - allocation_method に基づく株数算出 calc_position_sizes を実装（risk_based / equal / score 対応、lot_size（単元）で丸め、aggregate cap のスケーリングを実装）。
  - portfolio/__init__.py で上記関数群をエクスポート。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等）を集計してレポート出力する CLI を追加。
    - デフォルトの Pass/Fail 基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。
- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - duckdb を使ったファクター計算モジュールの骨格を追加。Momentum/Value/Volatility/Liquidity 等の設計方針と定数を定義（関数 calc_momentum などの実装開始）。

### Changed
- 監視・実行の DB ハンドリング方針
  - 監視 (run_monitoring) は環境設定にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する仕様。
  - 実行 (run_execution) は paper_trading 環境時に paper_sqlite_path を使うことで本番 DB と完全分離する仕様を導入。
- ログの標準化
  - setup_logging を全起動スクリプトで呼び出すことでログ出力の挙動を統一。ログディレクトリ作成失敗時にフォールバックする挙動を明示。

### Fixed
- .env パースの堅牢化
  - export プレフィックス、引用符・エスケープ、インラインコメント取り扱いの不備に対処（config._parse_env_line の実装）。
- ポジションサイズ計算の丸め・スケーリング
  - 単元（lot_size）での丸め処理および aggregate cap 超過時のスケーリングと再配分ロジックを実装し、予期しない投下金額超過に対処。

### Notes / Implementation details（重要）
- 環境変数名・デフォルトパス
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START, KABUSYS_ENV, MONITOR_POLL_INTERVAL などが使用されます。各モジュールのデフォルト値や検証は Settings / validate_config で定義されています。
- 停止制御（Kill/Stop フラグ）
  - run_execution/run_monitoring はプロジェクト内 data/stop_requested.flag の存在を監視して安全に停止する仕組みを採用。
- Paper Trading
  - paper_trading 環境は実取引と分離され、専用 SQLite DB に記録されて検証・レポートが可能。
- 実運用上の注意
  - Settings.env の値は "development" / "paper_trading" / "live" のみ許容。live 環境では LINE 通知設定や kill flag の設定に注意する必要あり（validate_config の警告参照）。
  - process_priority の設定は権限に依存し、失敗時は警告ログで継続する。

以上。コード内のドキュメント文字列やログメッセージ・CLI ヘルプ等をベースに CHANGELOG を作成しました。追加で修正履歴の粒度（例えば個々のコミット単位の記載）やリリースノート文面の調整が必要であれば指示してください。