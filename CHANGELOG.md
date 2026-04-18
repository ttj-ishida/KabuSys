# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能群を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録する仕組みを用意。
    - 起動時にプロセス優先度を "high" に設定するフローを追加。
    - 停止制御: data/stop_requested.flag の検出で安全に停止する。実行中の PID を data/execution.pid に書き出す。
    - duckdb を分析用 DB として併用。
  - run_monitoring: SystemMonitor ポーリングループ用起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を参照して動作。
    - 停止フラグ検出でループを終了する仕組みを実装。
- 設定管理・CLI
  - config.py: 環境変数/.env 読み込みロジックを追加。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロード（OS 環境変数は保護）。
    - _parse_env_line によりシングル/ダブルクォートや export 形式、行内コメント等を考慮した .env パーサを実装。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、しきい値やフラグ等）をプロパティで安全に取得するようにした。
    - 環境名検証（development / paper_trading / live）や PAPER_FILL_MODE のバリデーション等を実装。
  - config_setup: .env を対話式に初期作成・更新するウィザード CLI を追加。
    - 入力ガイド、既存値の再利用、シークレットマスキング、保存確認などを実装。
    - デフォルトや説明付きの設定項目一覧を提供（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
  - validate_config: 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス存在チェック、YAML パース（PyYAML がある場合）などを実施。
    - --strict モードで警告をエラー相当に扱うオプションを提供。
    - 本番環境向けの追加ガード（LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保管）を標準設定するユーティリティを追加。
    - ログレベル・ログディレクトリの解決順を定義し、既存ハンドラの二重設定を防止する処理を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する耐障害性を持たせた。
  - utils/process_priority.py:
    - psutil を用いて Windows / POSIX を吸収するプロセス優先度設定機能（high/normal/low）を追加。
    - CPU affinity を設定する set_cpu_affinity() も実装し、権限不足や未対応 OS 時は警告を出して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抜粋ロジックを実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限アルゴリズム（既存保有を基に新規候補を除外）を実装。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知のレジームは警告して 1.0 をフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウンを実装。
    - cost_buffer を考慮した保守的なコスト見積と、端数配分アルゴリズム（fractional remainder に基づく lot 単位追加配分）を実装。
- Paper Trading 向けツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）から期間指定で検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg, max, P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ生成、安全な DB 存在チェックと OperationalError フォールバックを実装。
- Research（部分実装）
  - research/factor_research.py:
    - ファクター計算モジュールを追加（モメンタム・MA200乖離・ATR 等を計画）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計で、日付/ウィンドウ長などの定数を用意。関数 calc_momentum の実装が始まっている（未完の箇所あり）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

注記:
- デフォルトのファイルパスや動作は環境変数で上書き可能（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR, LOG_LEVEL, MONITOR_POLL_INTERVAL など）。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 本リリースは初期実装のため、factor_research の一部など未完成の機能が含まれます。今後のバージョンでテスト強化・機能追加・バグ修正を行う予定です。