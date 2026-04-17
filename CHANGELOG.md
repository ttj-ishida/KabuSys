# Changelog

すべての注目すべき変更をこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。  
リリース日付はパッケージのスナップショット取得日を使用しています。

全般
- 初期バージョン: 0.1.0
- バージョン番号はパッケージ定義 (kabusys.__version__) に合わせています。

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成
  - パッケージ初期化とバージョン管理 (kabusys.__version__ = "0.1.0") を追加。

- 環境設定 / 設定読み込み
  - Settings クラス (kabusys.config) を実装。
    - 環境変数／.env ファイルから各種設定値を取得。
    - 自動 .env ロード機能（プロジェクトルートの .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境判定プロパティ: is_live / is_paper / is_dev。
    - 各種設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*（任意）、DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）、PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）、PID/KILL フラグパス、しきい値（CPU/MEMORY/DISK）等。
    - 不正な値や未設定の必須環境変数に対する明示的な例外/検証ロジック。

  - .env 読み込みのパーサ実装
    - export 形式、クォート付き値、インラインエスケープ、コメント処理などに対応。
    - OS 環境変数を保護する protected オプションにより上書き制御を実現。

- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装。
    - .env の初期作成・更新を支援。
    - 入力項目定義、シークレット項目のマスク表示、選択肢、デフォルト表示、キャンセル処理。
    - 最終的に .env を生成（.env ファイルのテンプレート化と書き込み）。

- 設定検証 CLI
  - validate_config.py を実装。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live の場合の安全ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を失敗扱いにできる。

- 実行・監視用起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。プロセス優先度を高に設定して起動。
    - Settings を用いて SQLite / DuckDB に接続。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBroker を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行。エンジンは別スレッドで run_session を実行し、stop_requested.flag により外部停止が可能。
    - 起動時に既に停止フラグがある場合は起動を中止。実行中に停止フラグを検出したら安全に engine.stop() を呼ぶ。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。プロセス優先度を高に設定して起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告ログを出力。
    - 監視ループは data/stop_requested.flag を監視して終了。KeyboardInterrupt ハンドリングあり。
    - 監視用 DB 初期化（init_monitoring_db）を保証。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様となっている。

- モニタリング DB 初期化（モジュール分離）
  - monitoring.monitoring_db モジュール（init_monitoring_db の存在を示唆）を参照する実装を追加（スクリプトから呼び出し）。

- Execution 系コンポーネント（呼び出し側）
  - ExecutionEngine, EngineConfig, OrderManager, OrderRepository, Reconciler, RiskManager, RiskConfig 等を run_execution から組み立てる想定でインポートし使用。

- ユーティリティ
  - process_priority.py を実装。
    - Windows と POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity(cpu_count) を追加。
    - psutil ベースで実装し、権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築（pure function）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順で上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で重み計算。全スコアが 0 の場合は等金額配分にフォールバックして警告ログを出力。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存ポジション比率が max_sector_pct を超える場合、新規候補から当該セクターを除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime（"bull","neutral","bear"）に応じた資金乗数を返す（デフォルト / フォールバック含む）。未定義レジームでは警告と 1.0 フォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: weights, candidates, portfolio_value, available_cash 等を基に各銘柄ごとの買付株数を計算。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - risk_based: risk_pct / stop_loss_pct から株数を算出し、単元株（lot_size）で丸める。
      - 最大ポジション上限（max_position_pct）と利用率上限（max_utilization）を考慮。
      - cost_buffer を加味した aggregate cap（利用可能現金を超える場合のスケーリング）実装。スケールダウン後の端数は lot_size 単位で残差（fractional_remainder）に基づき再配分。
      - 価格未取得（<=0）の銘柄はスキップし適切にログ出力。

- 研究 / ファクター計算
  - research.factor_research を実装（DuckDB を使用）。
    - calc_momentum: mom_1m/3m/6m、ma200 乖離（ma200_dev）を計算。必要な過去ウィンドウ長やデータ不足時の None 扱い。
    - calc_volatility: ATR (20日) / 相対 ATR / 20日平均売買代金 / 出来高比などを計算するための基盤クエリを含む（高/低/前日終値の NULL 伝播を制御）。
    - DuckDB 上の prices_daily テーブルを参照して計算し、(date, code) 単位の辞書リストを返す設計。データ不足に対する安全措置あり。

- ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - P95 計算ユーティリティを実装。閾値判定（稼働率 >= 99% 等）に基づく PASS/FAIL 出力。
    - 日付フィルタ（--from, --to）、--db オプションに対応。DB ファイル不存在時のエラーメッセージ。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（既存の OS 環境変数を上書きしない、.env.local を上書き可能だが protected リストは尊重）。

---

Notes / 運用メモ
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
  - PID/フラグ: data/execution.pid / data/stop_requested.flag / data/kill.flag（Settings によりカスタマイズ可能）
- 環境変数の主なキー:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 任意/推奨: KABUSYS_ENV (development|paper_trading|live)、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、MONITOR_POLL_INTERVAL、LOG_LEVEL、LINE_* 等
- run_monitoring/run_execution/run_* スクリプトはモジュールとして実行可能（python -m kabusys.run_monitoring 等）。
- run_monitoring は監視用テーブル初期化を保証するために init_monitoring_db を常に呼ぶ設計（環境に関係なく本番 sqlite_path を使用）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB を使用し、本番 DB とデータを分離する。

フィードバックや追加したい変更点（ドキュメントの追記、既知の制限項目の明示など）があれば知らせてください。必要に応じて掲載内容を調整して更新します。