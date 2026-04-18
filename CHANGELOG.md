# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般
- 初期バージョンをリリースしました（バージョン: 0.1.0, 日付: 2026-04-18）。
- パッケージメタ情報: `__version__ = "0.1.0"`。

v0.1.0 - 2026-04-18
------------------

Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - プロセス優先度を起動時に "high" に設定（utils の set_process_priority を使用）。
    - 監視は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用して DB に接続する仕様になっている点を明示。
    - 停止はプロジェクト内 `data/stop_requested.flag` の存在検知で行う（優雅な終了処理を実装）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（`data/paper_trading.db`、環境変数で上書き可能）に記録して本番 DB と分離。
    - プロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止監視（stop flag 検知による停止）を実装。
    - 実行中の PID を `data/execution.pid` に扱う（Engine に pid_file を渡す）。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機構を追加（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - `.env` / `.env.local` の読み込み順序を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - .env パーサーは `export KEY=val` 形式、クォート文字列、インラインコメントを適切に処理する実装。
    - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得できるようにした（例: `jquants_refresh_token`, `kabu_api_password`, `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種閾値など）。
    - `KABUSYS_ENV` / `LOG_LEVEL` などの値検証を実装（許容値以外は ValueError）。
    - `PAPER_FILL_MODE` の妥当性チェック（"instant"|"partial"|"never"|"reject"）を実装。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 複数の設定項目を対話的に入力でき、シークレットはマスク表示。最終確認後に .env を書き出す。
    - デフォルト値・説明文を用意し、既存の .env を読み込んで再利用可能。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML が利用可能なら）パース検証、KABUSYS_ENV=live 時の追加注意点などを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（daily、30日保持）を設定する共通ユーティリティを追加。
    - 既存ハンドラの重複防止（クリア→再設定）、ログディレクトリ作成のフォールバック（作成失敗時はファイルハンドラをスキップ）、ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
    - StreamHandler は stdout を使う（cron 等で stdout/stderr をリダイレクトしやすくするため）。

  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度を設定するユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - アクセス権限不足等で失敗した場合は警告を出してスキップする安全設計。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有のセクター別エクスポージャーを計算し、上限を超えたセクターの新規候補を除外する。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method: "risk_based"|"equal"|"score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、全体の投下上限（available_cash に対する aggregate cap）、cost_buffer を考慮したスケーリングと残差処理を実装。
    - 価格欠損時のスキップやログ出力などの安全処理を含む。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシなどを計算。
    - デフォルト閾値を定義（例: uptime >= 99.0%、fill_rate >= 90.0%、P95 latency <= 200 ms）。
    - SQLite の `system_status`, `trade_logs`, `risk_logs` テーブルから集計クエリを実行してレポートを出力。日付レンジ指定オプションをサポート。
    - DB が存在しない場合のエラーメッセージを実装。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してファクターを計算する方針を実装（calc_momentum 等の関数を実装開始）。

Security
- 特になし。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 注意事項
- run_monitoring は意図的に KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用します。環境分離を期待する場合は運用時に注意してください。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は実取引と完全に分離する設計ですが、環境変数やパス設定を確認してから運用してください。
- config の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。パッケージ配布後やテスト環境で自動ロードを望まない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- research/factor_research の一部実装は継続開発中です（本リリースではファクター計算の骨子と設計方針を含む）。

今後の TODO（想定）
- factor_research の完全実装（全ファクターと正規化ユーティリティ統合）。
- ExecutionEngine / BrokerClient の詳細なテスト、および paper/live クライアントの更なる分離・モック強化。
- ログ回転やディレクトリ権限失敗時の運用ドキュメント整備。