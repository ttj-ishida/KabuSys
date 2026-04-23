CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット
-----------
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。
- バージョンごとに日付を付与しています。

[Unreleased]
------------
（なし）

[0.1.0] - 2026-04-23
-------------------
Initial release — 日本株自動売買システム「KabuSys」の初回公開リリース。

Added
- コアパッケージ構成を追加
  - kabusys パッケージの初期化（__version__ = "0.1.0"）。
- 実行・監視用の起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、ペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行 PID を data/execution.pid に出力（pid_file パスは設定可能）。
    - RiskManager のデフォルトパラメータ（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 停止フラグでループ終了。KeyboardInterrupt での安全終了処理。
- 設定管理
  - config.py
    - Settings クラスを追加。環境変数から各種設定を取得する。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env / .env.local の読み込みルール（OS 環境変数を保護）。
    - 必須値チェック用の _require と各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値、KABUSYS_ENV/LOG_LEVEL 判定など）。
    - PAPER_FILL_MODE の有効値チェック（instant|partial|never|reject）。
    - KABUSYS_ENV の有効値: development / paper_trading / live。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成 / 更新する CLI。
    - 各種項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話で設定。シークレットはマスク表示。
    - .env のテンプレート書き込み機能を備える。
  - validate_config.py
    - 起動前検証用 CLI。必須環境変数、不正な KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML がある場合）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプト（コマンドライン）。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）など。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全て 0 の場合には等配分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - apply_sector_cap は既存保有のセクター別エクスポージャ計算に基づき候補をフィルタ。unknown セクターは上限適用外。
    - calc_regime_multiplier は regime (bull/neutral/bear) に応じた乗数を返す（未知値は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）。
    - allocation_method: risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
- utils ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティ（setup_logging）。
    - stdout StreamHandler と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテート、30 日保持）をルートロガーに設定。既存ハンドラは一旦クリア。
    - LOG_DIR / LOG_LEVEL 環境変数対応。ファイル出力に失敗した場合はコンソール出力にフォールバック。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。
    - Windows / POSIX（Linux/Mac/FreeBSD）を考慮。権限不足時は警告を出してスキップ。
- monitoring 周辺
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。
  - SystemMonitor を利用した監視ループの導入（run_monitoring から起動）。
- research/factor_research.py
  - ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）の基礎的実装方針と定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
  - モメンタム計算（calc_momentum）の設計・骨格を追加（詳細実装はモジュール内で記述）。

Changed
- （新規リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 運用メモ
- 環境変数自動読み込み
  - プロジェクトルートが検出できる場合、起動時に .env（優先度低）→ .env.local（優先度高）を自動ロードする。
  - OS 環境変数の保護により既存の環境変数は上書きされない（ただし .env.local は override=True）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト: 60）
- 停止／制御フラグ
  - data/stop_requested.flag: run_execution / run_monitoring が存在検査して安全停止を行う。
  - PID ファイル: data/execution.pid（run_execution が使用）。
- Paper trading
  - paper_trading 環境では MockBrokerClient を利用し、本番 DB と完全分離した専用 SQLite に記録される（データ分離により安全に検証可能）。
- ログとファイル書き込み
  - ログディレクトリが作成できない環境ではファイル出力を無効化して stdout のみで動作する（警告出力）。

アップグレード / 移行手順
- 既存の .env を使用する場合、config_setup のウィザードや validate_config を使用して設定の整合性を確認してください。
- 本番（live）環境で起動する前に validate_config を実行し、LINE 通知設定など本番向けガードを確認してください。
- run_execution/run_monitoring をデーモン化（systemd 等）して運用する場合は、ログディレクトリと data/ 以下のパス（stop flag, pid file）への書き込み権限を確認してください。

付記
- 本 CHANGELOG はコードベース（src/ 以下）の内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリースに含める変更点（バグ修正、既知の問題、互換性情報など）をプロジェクトの実際の変更履歴に合わせて追記・調整してください。