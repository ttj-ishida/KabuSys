# Changelog

すべての重要な変更点は Keep a Changelog の形式で記録します。  
このファイルは、コードベースのスナップショット（初期リリース相当）から推測して作成した一覧です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点で未リリースの作業はありません）

## [0.1.0] - 2026-04-21
初期リリース（コードベースのスナップショットに基づくまとめ）。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、DB 接続、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、エンジンのバックグラウンド実行と停止フラグ処理を実装。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。BrokerClientFactory を通して MockBrokerClient を利用する想定。
    - 実行 PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイルの検出によりループ終了。例外時はログに出力して次ポーリングまで待機。

- 設定関連
  - config.py
    - Settings クラスで環境変数を型付きプロパティとして集約（DB パス、KABUSYS_ENV、ログレベル、閾値等）。
    - .env/.env.local の自動読み込み機能を追加（プロジェクトルート自動検出: .git または pyproject.toml を起点）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env 行のパースを堅牢化（export プレフィックス、クォート値のエスケープ、インラインコメント、無効行のスキップ等）。
    - PAPER_FILL_MODE（paper trading の fill モード）や PAPER_TRADING_SQLITE_PATH 等の paper_trading 向け設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。必須/任意項目、シークレット入力、デフォルト値、保存確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML 未導入時は警告）、本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意）を実装。--strict オプションをサポート。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、LOG_DIR/LOG_LEVEL による上書き、ファイルハンドラのフォールバック処理、30 日分保持を実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。psutil を利用して high/normal/low を設定。権限不足や未対応 OS の際は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの選別（スコア降順、タイブレーク: signal_rank）と候補抽出 select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有比率を元に新規候補を除外）と市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear マップ）を実装。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装。allocation_method = "risk_based" / "equal"/"score" をサポート。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り、残差に基づく追加配分ロジックなどを搭載。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。paper_trading SQLite（既定: data/paper_trading.db）から統計を集計し、稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を出力する。しきい値はソース内で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - tools/__init__.py を追加（パッケージ化用）。

- 監視関連
  - monitoring モジュールに関する初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring に統合して監視テーブルの存在を保証。

- 研究用モジュール（下書き）
  - research/factor_research.py
    - DuckDB を使ったファクター計算の枠組みを追加。モメンタム（1M/3M/6M、MA200 乖離）、ATR、出来高等の計算を想定する設計。関数 calc_momentum の雛形や定数が作成済み（実装は続行中／一部未完）。

### Changed
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定（パッケージ初期バージョンの明示）。

### Fixed / Robustness improvements
- config._load_env_file / _parse_env_line
  - export プレフィックスやクォート含む値、バックスラッシュエスケープ、インラインコメントの取り扱いを堅牢化し、.env の柔軟な記述に対応。
  - .env.local の override 挙動を導入し、既存 OS 環境変数は protected として上書き防止。
- logging_setup
  - ログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップし、コンソール出力にフォールバックすることで起動失敗を回避。
- process_priority / set_cpu_affinity
  - 未対応 OS や権限不足を考慮した例外ハンドリングと警告出力を追加。

### Notes / Behavior decisions
- run_monitoring は監視用 DB として Settings.sqlite_path（本番用）を常に使用する実装になっている（監視は環境に依存しない設計）。
- run_execution は paper_trading 環境では paper_sqlite_path を使用することで発注履歴等を本番 DB と分離する設計。
- ログは stdout に出力されるため、cron や Task Scheduler からの起動でもリダイレクトしやすくなっている。
- RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）は ExecutionEngine 側で設定される（run_execution のコード参照）。

### Known limitations / TODOs
- research/factor_research.py は一部実装が未完（ファクター計算の詳細実装が途中）。
- portfolio/position_sizing の価格欠損時のハンドリングに TODO コメントあり（フォールバック価格の導入検討）。
- 単元株情報（lot_size）を銘柄別に持つ拡張は未実装（将来的な拡張案）。
- 一部のユーティリティは psutil や PyYAML 等の外部依存があるため、環境によっては機能限定となる（validate_config は PyYAML 未導入時に YAML 検証をスキップ）。

---

この CHANGELOG はコードの実装内容を読み解いて作成した推測に基づくものです。実際のリリースノートや追加された変更と差異がある場合は、該当箇所の修正・追記をお願いします。