# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

- リリース日付はコードベースから推測して記載しています。  
- 内容はソースコードの実装・ドキュメント文字列から推測してまとめたものです。

## [0.1.0] - 2026-04-21

### 追加
- 全体
  - 初回リリース相当の機能群を追加。モジュール構成、CLI・ユーティリティ、コアロジックを含む。

- 設定管理
  - 環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から検出して自動で .env / .env.local を読み込む機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env ファイルの堅牢なパーサを実装（export プレフィックス、クォート/エスケープ、インラインコメント対応）。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DBパス / Paper Trading 設定 / 監視閾値 / ログレベル 等）を型付きプロパティで取得可能に。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの値検証を実装（不正値は例外を発生）。

  - 対話式設定ウィザードを追加（kabusys.config_setup）。
    - .env の初期作成・更新を対話的に行う CLI。シークレット項目は表示をマスク。
    - デフォルト値の提示、既存 .env の読み込み、最終確認、ファイル書き込み機能を提供。

  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数やパス・YAML 設定ファイル（config/*.yaml）の存在・パース確認を行う。
    - --strict オプションで警告を FAIL 扱いにでき、本番環境向けの追加チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性）を行う。

- 実行／監視ランナー
  - ExecutionEngine 起動スクリプトを追加（run_execution.py）。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory により本番/モックのブローカークライアントを自動選択。
    - ExecutionEngine を別スレッドで起動し、 data/stop_requested.flag による安全な停止（PID ファイル管理）を実装。
    - RiskManager / OrderManager / Reconciler / OrderRepository 等の組み立てを行うサンプル構成を追加。
  - SystemMonitor 起動スクリプトを追加（run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用して監視データを一元化。
    - 停止フラグファイル検知、例外時のログ出力、KeyboardInterrupt ハンドリングを実装。

- データベース／分析
  - DuckDB と SQLite を併用する設計を導入（Settings に DUCKDB_PATH, SQLITE_PATH）。
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db）をスクリプト起動時に呼び出し、冪等にテーブル存在を保証。

- ロギング／プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout（StreamHandler）への出力と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力をルートロガーに設定。
    - LOG_DIR 環境変数、アプリ名指定、ログレベル解決の優先順を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, macOS 等）を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を特定コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）を追加。
    - select_candidates（スコア降順で上位 N を選択）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）を追加。
    - apply_sector_cap：既存ポジションを基にセクター上限を判定して候補を除外。
    - calc_regime_multiplier：market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック）。
  - 株数決定・リスク制限（kabusys.portfolio.position_sizing）を追加。
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリング、端数（fractional）処理による追加配分ロジックを実装。
    - cost_buffer による保守的なコスト見積りを考慮。

- Paper Trading 検証ツール
  - paper_verification_report スクリプトを追加（kabusys.tools.paper_verification_report）。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間を指定してレポートを出力。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（平均、最大、P95）などを集計。
    - P95 計算、閾値に基づく PASS/FAIL 判定を実装（閾値はソース内定数で定義）。

- リサーチ（部分実装）
  - factor_research モジュールの基礎を追加（kabusys.research.factor_research）。
    - Momentum / Value / Volatility / Liquidity 等の計算を行う方針と定数を実装。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - （注）ファイル末尾が途中で切れているため一部実装は未完。

### 変更
- パフォーマンスと堅牢性
  - run_monitoring/run_execution でプロセス優先度を起動早期に設定するように変更（set_process_priority("high")）。
  - run_execution で Paper Trading 環境時に専用 DB を使用するよう分離（安全のため）。

- .env 読み込み順序
  - 自動読み込みの優先順位を OS 環境変数 > .env.local > .env に明示的に定義し、OS 環境変数を保護（上書き禁止）する仕組みを導入。

- ログ出力
  - StreamHandler を stdout に固定（cron / Task Scheduler などで stdout/stderr を一本化してリダイレクトする運用に合わせる）。

### 修正
- 環境変数パースの堅牢化
  - _parse_env_line がクォート内部のエスケープやインラインコメントの扱いを適切に処理するようにしたため、複雑な値（改行やシークレット）を含む .env の読み込みが安定。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL の値が不正（非数値や 0 以下）の場合、デフォルト（60 秒）にフォールバックし、警告ログを出力するようにした（run_monitoring）。

- DB 初期化の冪等化
  - 監視用 DB 初期化（init_monitoring_db）は既存テーブルの存在を許容し、何度呼んでも安全に動作するように実装。

- 例外ハンドリング強化
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続し、例外のトレースをログに出力するようにした。

### 既知の問題 / 注意点
- factor_research モジュールはファイル末尾が途中で切れているため、モメンタム計算など一部関数が未完（実装継続が必要）。
- position_sizing の価格欠損時の挙動に注意（price が 0.0 の場合はエクスポージャーの過少見積りが起こりうる旨の TODO コメントあり）。
- process_priority / cpu_affinity の設定は権限不足や環境依存のため失敗する可能性があり、その際は警告を出してスキップする設計。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合、ファイル出力はスキップされコンソール出力のみになる。

--- 

将来的なリリースでは、factor_research の完成、テストカバレッジの追加、ExecutionEngine/EngineConfig の詳細公開、さらなるエラーハンドリング強化・監視メトリクス拡充などを想定しています。