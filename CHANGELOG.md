# Changelog

すべての注目すべき変更を記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報: kabusys.__version = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル data/stop_requested.flag を検知して安全終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に集約）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の MockBrokerClient と paper_trading DB を使用（本番 DB と分離）。
    - スレッドで ExecutionEngine を起動し、stop フラグで終了を制御。
    - execution.pid を PID 管理に使用。

- 設定・環境変数関連
  - config.py:
    - .env 自動ロード機能（.env, .env.local）を実装。OS 環境変数は保護され、.env.local は上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 複数の設定プロパティを提供（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値など）。
    - 環境変数の必須チェック用ヘルパー _require を提供。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - J-Quants / kabuステーション / DB パス / ログレベル / Kill Switch 設定などを対話で編集・保存可能。
  - validate_config.py: 起動前検証 CLI を実装。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在とパース検証（PyYAML が利用可能な場合）。
    - --strict モードで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なロギング設定関数 setup_logging() を追加。
    - stdout 出力の StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ファイル出力失敗時はコンソールのみで継続。
    - LOG_DIR / LOG_LEVEL の解決順を実装。
  - utils/process_priority.py:
    - プロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分吸収、アクセス権限エラーは警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア順で候補選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター別上限チェックと候補除外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数、未知レジームはフォールバック）
  - portfolio/position_sizing.py:
    - calc_position_sizes（risk_based / equal / score の配分方式に対応、lot_size 単位で丸め、aggregate cap によるスケールダウンと残余配分処理）

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定するレポートを標準出力に表示。
    - デフォルト DB パスは data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで上書き可能。
    - 判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。

- リサーチ
  - research/factor_research.py（ファクター計算基盤の雛形を追加）
    - Momentum / Value / Volatility / Liquidity 等の計算方針および定数を定義。DuckDB 接続を受けて prices_daily / raw_financials から計算する設計。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制限・注意点
- run_monitoring は「監視用 DB を常に本番 sqlite_path に接続する」設計のため、監視データは環境設定に関わらず本番の SQLite に格納されます（意図的な挙動）。
- run_execution は paper_trading 環境時に paper_trading 用の DB を使用して本番 DB と分離します。紙上検証と本番データの混同に注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で実行されます。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正な値を与えると ValueError が発生します。
- position_sizing の価格フォールバックは未実装（price が 0.0 の場合、エクスポージャーが過少見積りされる可能性あり）。将来的に前日終値などのフォールバックを検討。

### マイグレーション / 設定メモ
- .env を使う場合は config_setup.py のウィザードで初期作成すると便利です。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ファイル出力先を変更するには LOG_DIR を設定してください。
- 監視ループのポーリング間隔を変更するには MONITOR_POLL_INTERVAL を秒で指定してください（正の整数、無効な値はデフォルト 60 秒にフォールバック）。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定することは推奨されません（Kill Switch が自動クリアされるため）。

--- 

今後の予定（例）
- research/factor_research の各ファクター実装完了（Momentum 等の SQL 実装を追加）。
- ExecutionEngine / Broker クライアント周りの詳細実装・テスト補強。
- 価格フォールバック・lot_size の銘柄別対応など、position_sizing の改善。