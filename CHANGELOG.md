CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このドキュメントはコードベース（src/ 以下）の内容から推測して作成した初期リリース向けの変更履歴です。

0.1.0 - 2026-04-18
-----------------

Added
- コア起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のスレッド実行をサポート。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を監視して安全に停止。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）を実装。
    - 強力な .env パーサ実装（export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント対応）。
    - アプリ設定を取得する Settings クラスを追加（DB パス、PID / Kill flag パス、しきい値、env 判定、paper_trading 用設定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を導入。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。代表的な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START）を扱う。
    - 既存 .env 読み込み、シークレットのマスク表示、保存前確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本検証を行う CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML が未インストールの場合はスキップして警告）を実装。
    - live 環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログ出力先（logs/<app_name>.log）とログレベルは引数・環境変数で指定可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ出力。
  - utils/process_priority.py
    - プラットフォーム差を吸収してプロセス優先度を設定するユーティリティを追加（Windows と POSIX をサポート、AccessDenied 等を安全に扱う）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア全てが 0.0 の場合は等金額配分へフォールバックし警告を出す実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実装する apply_sector_cap。既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear とフォールバック）。
    - 一部ケース（price が欠損した場合の取り扱い）について将来改善を示す TODO を含む。
  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、最大ポジション比率・利用率・コストバッファを考慮した aggregate cap によるスケールダウンと再配分ロジックを実装。
    - 将来的な銘柄別 lot_size 拡張の TODO コメントを含む。

- 解析・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。コマンドラインから期間指定（--from/--to）可能。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95 を含む）を算出し、基準値との比較で PASS/FAIL を判定。
    - P95 計算ユーティリティ、欠損テーブルに対する耐性（OperationalError を捕捉して N/A 扱い）を実装。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py（骨格実装）
    - Momentum / Value / Volatility / Liquidity 系ファクターを計算する方針と定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（calc_momentum 等の関数を実装開始）。※一部実装が途中のまま（ファイル末尾の関数が途中で切れている）。

Other notable points
- 環境変数一覧（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- プロセス優先度設定は起動直後に High に設定するのが既定の挙動（run_execution, run_monitoring）。
- 停止制御は data/stop_requested.flag（および PID / kill flag のパス設定）で行う設計。
- データベース接続は sqlite3（監視・paper_trading）と duckdb（分析用）を併用。
- ログは stdout へ出力されるため、cron/タスクスケジューラ実行時にリダイレクトが容易。

Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾に未完成箇所あり）。
- risk_adjustment.apply_sector_cap 内で price が欠損した場合のフォールバック価格ロジックは未実装（コメントで将来的拡張を示唆）。
- position_sizing: 銘柄別単元（lot_size）を将来的にマスタから取得する設計にする TODO が残る。
- 一部外部モジュール（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）はこの差分に依存しているが、本 changelog は公開されているファイルのみから推測して記載しているため、実際の統合時にはさらに詳細な検証が必要。

Security
- 重要なトークン類（J-Quants / kabu API）は .env に保存する想定。config_setup のヘッダで .env を絶対に Git にコミットしないよう注意喚起をしている。

---

参考: パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に基づく初回リリース想定。

もしリリース日やセクションの分け方をプロジェクトの実際の運用スタイル（Unreleased セクションの追加など）に合わせて調整したければ、教えてください。必要に応じて英語版や短いリリースノート（メール向け）も作成します。