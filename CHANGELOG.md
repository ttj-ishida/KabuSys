CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 基本リリース: KabuSys 初期実装を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory により本番/モックブローカーを生成。
    - 停止制御: data/stop_requested.flag を監視し停止処理を実行。実行中 PID を data/execution.pid に格納する想定。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててセッションを別スレッドで実行。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を提供。initial_portfolio_value は broker.get_available_cash() によって取得。

- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 例外発生時はログに出力して次のポーリングへ継続。

- 設定管理
  - config.py: 環境変数/.env の読み込みと Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml から検出し、.env/.env.local を自動ロード（OS 環境変数を上書きしない、安全なロード順）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 閾値等）。
    - PAPER_FILL_MODE の入力検証（"instant", "partial", "never", "reject" のみ有効）。
    - KABUSYS_ENV / LOG_LEVEL の値検証。
    - settings = Settings() をモジュールレベルで提供。

- 設定支援・検証 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 各設定項目のプロンプト、既存 .env の読み込み、シークレット値のマスク表示、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース確認、本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - psutil を使ったプロセス優先度設定（Windows の priority class / POSIX の nice 値）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足等で設定できない場合は警告出力してフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超えると当該セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer（スリッページ・手数料見積）を考慮した aggregate cap スケーリングロジックを実装。
    - risk_based では risk_pct と stop_loss_pct に基づくポジションサイズ算出。
    - 価格欠損時はスキップし、ログで理由を出力。

- 解析・ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値はソース内定数で定義（例: 稼働率 >= 99.0%、P95 <= 200ms 等）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。P95 計算、欠損データハンドリングを実装。

- リサーチ基盤（ファクター計算の骨子）
  - research/factor_research.py:
    - Momentum などファクター計算の設計と calc_momentum の実装開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。モメンタム・MA200 などの算出方針を定義（実装は継続）。

Changed
- パッケージメタ
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

Fixed
- なし（初回リリース）

Notes / Implementation details
- run_monitoring は monitoring 用 DB を初期化する init_monitoring_db を呼ぶが、監視用途は本番 sqlite_path を参照する（環境に依存しない設計）。
- .env 自動読み込みは OS 環境変数を優先し、.env.local を .env の上位で上書きする。自動ロードを無効化するフラグあり。
- ログハンドラは既存ハンドラを一旦 flush / close してから再設定するため、複数回 setup_logging を呼んでも二重出力が発生しない。
- process_priority の設定は権限不足等で失敗した場合に安全にフォールバックする（警告ログのみ）。
- position_sizing の aggregate cap スケーリングは、端数の配分を lot_size 単位で残差順に再配分することで安定した再現性を確保。

Deprecated / Removed / Security
- なし

今後の予定（例）
- research/factor_research の各ファクター算出ロジックの完成。
- ExecutionEngine / SystemMonitor の追加ユニットテスト整備。
- 銘柄ごとの lot_size マスタ対応（position_sizing の拡張）。
- UI やダッシュボード連携用の出力形式追加。