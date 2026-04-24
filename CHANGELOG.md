# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
日付はこのリリース作成日（仮）です。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報: kabusys のバージョンを `__version__ = "0.1.0"` に設定。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI ラッパー。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - エンジンの PID 管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）対応。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 背景スレッドで engine.run_session を実行し、停止フラグを監視して安全に停止する仕組み。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視系は KABUSYS_ENV に関わらず監視用 sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 環境設定関連の CLI ツールを追加。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新するユーティリティ。
    - 設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 周り、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）をサポート。
    - 既存 .env の読み込み、シークレット値のマスク表示、保存確認を行う。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML ファイルの存在およびパース検証（PyYAML が存在する場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- 設定 / 環境管理モジュールを追加。
  - config.py
    - Settings クラスにより環境変数を集中管理。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE のバリデーション、PID/kill flag パス、監視しきい値、LOG_LEVEL、env 判定機能等）。
- ポートフォリオ構築モジュールを追加（pure functions）。
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用ロジックを提供（既存保有や売却予定を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - position size 計算（risk_based / equal / score）を実装。lot_size（単元株）に基づく丸め、per-stock および aggregate cap のスケーリングロジック、cost_buffer を考慮した安全な配分。
- 監視 / 検証ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、レイテンシ（avg/max/P95）などを算出し PASS/FAIL を判定する閾値を用意。
    - SQLite DB（デフォルト: data/paper_trading.db）から system_status / trade_logs / risk_logs を参照。
- ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティ。コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）を設定。
    - LOG_DIR / LOG_LEVEL 環境変数または関数引数で設定可能。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - utils/process_priority.py
    - psutil を利用してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。Windows / POSIX の差分を吸収し、失敗時は警告を出してスキップ。
- research/factor_research.py（ファクター計算モジュール）を追加（モメンタムなどの設計・一部実装）。
  - DuckDB を利用して prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 系の計算を行う設計。

### 変更 (Changed)
- ログ出力の挙動を統一。
  - setup_logging() により全起動スクリプトで共通のフォーマット・ファイルローテーションを使用するようにした。
  - StreamHandler は stdout を使用（cron 等でリダイレクトする運用を想定）。
- DB の使用ルールを明確化。
  - 監視系（run_monitoring）は KABUSYS_ENV に依らず「監視用」sqlite_path を使用（デフォルト: data/monitoring.db）。
  - 実行系（run_execution）は paper_trading の場合に専用の paper_sqlite_path を使用して本番 DB と分離。
- .env の自動ロード機能を追加（config.py）。
  - プロジェクトルートを検出して .env と .env.local を読み込む。OS 環境変数は保護される（上書きされない）。
  - .env 読み込みの挙動は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 環境変数パースの強化。
  - _parse_env_line() により export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理をサポート。
- Paper Trading の挙動を明文化。
  - PAPER_FILL_MODE の有効値チェックを実装（instant / partial / never / reject）。不正値で ValueError を送出するように変更。

### 修正 (Fixed)
- run_monitoring のポーリング間隔取得で不正値を検出してデフォルトにフォールバックするように修正（MONITOR_POLL_INTERVAL の負値や非整数をハンドリングし、警告ログを出力）。
- logging_setup: ログディレクトリ作成失敗時やファイルハンドラ作成失敗時に安全にフォールバックするよう改善。
- process_priority: 未対応 OS, 権限不足や psutil の実装差異に対して警告を出し、起動を妨げないように修正。

### 破壊的変更 (Breaking Changes)
- PAPER_FILL_MODE に対するバリデーションが導入されました。以前は自由な文字列が許容されていた場合でも、現在は "instant" / "partial" / "never" / "reject" のみが有効です。不正な値が設定されていると起動時に ValueError が発生します。
- 自動 .env ロードがデフォルトで有効になっています。環境に依存した挙動を期待していた運用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。

### セキュリティ (Security)
- シークレット値の扱いに配慮。
  - config_setup.py のウィザードでシークレット項目は入力画面でマスクまたは表示を抑制する配慮を実装。
  - README 等で .env を Git にコミットしないよう注記（.env 生成ヘッダに注意書きを追加）。

### 注意事項 / 既知の問題 (Notes / Known issues)
- research/factor_research.py は設計に沿った関数群を実装していますが、ファイル末尾での実装が途中で終わっている可能性があります（calc_momentum の実装が続く想定）。今後の拡張で完全実装予定です。
- process_priority, set_cpu_affinity は実行環境の権限や psutil のサポート状況に依存します。権限不足時は警告が出て処理はスキップされます。
- position_sizing と risk_adjustment は現在メモリ内計算（DB 参照なし）で動作します。将来的に lot_size を銘柄別に持たせる等の拡張が示唆されています（TODO コメントあり）。
- validate_config の YAML 検証は PyYAML がインストールされていない場合はスキップされます。

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / SystemMonitor の E2E テスト強化。
- strategy / data モジュールとの統合テスト、ドキュメント充実化（PortfolioConstruction.md / StrategyModel.md に基づいた例の追加）。