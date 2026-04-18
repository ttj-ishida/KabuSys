# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載します。  
このファイルはリポジトリの現在のコードベースの状態から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は Paper 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）を検知してエンジン停止処理を行う。起動前にフラグが立っている場合は起動をスキップ。
    - 実行時に PID ファイル（data/execution.pid 等）を扱うサポートを含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。1 秒未満や不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB 初期化を行い（init_monitoring_db）、Monitoring は環境に関係なく本番用の sqlite_path を使用する設計。
    - 停止フラグの検知、例外発生時のログ化とリトライ（次ポーリングまで待機）を実装。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から設定値をプロパティ経由で取得する統一 API を提供。
    - .env 自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パースの堅牢化: export 句対応、クォート文字列のエスケープ処理、インラインコメントの扱いなどをサポート。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE（バリデーションあり）、PID/KILL フラグパス、閾値系設定、LOG_LEVEL、KABUSYS_ENV 等）を定義。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - シークレット項目はマスク表示、既存 .env の読み込みとデフォルト値の再利用をサポート。
    - 保存前の確認プロンプトと .env の書き込みロジックを実装。
  - validate_config.py
    - .env と config/*.yaml（存在確認および PyYAML があればパース検証）を事前検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス（親ディレクトリ存在チェック）、本番向けガード（LINE通知設定や KILL_FLAG_CLEAR_ON_START の警告）などの検査を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（<log_dir>/<app_name>.log、日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを実装。
    - デフォルトでは logs/ ディレクトリを使用。出力を stderr ではなく stdout にすることで外部ジョブスケジューラからのログ統合を容易にしている。
  - utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX の差分吸収）。`set_process_priority("high" | "normal" | "low")` を提供。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供（アクセス権限やプラットフォームによる失敗は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジーム（bull/neutral/bear）に応じた投下資金乗数 calc_regime_multiplier（未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジック（allocation_method: "risk_based" | "equal" | "score"）を実装。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケールダウン）を実装。
    - cost_buffer を用いた保守的コスト見積り、スケールダウン時の残差（fractional remainder）に基づく lot_unit 追加配分ロジックを実装。

- 研究 / ファクター計算（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials を用い、Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計を追加（モジュール構成と定数、calc_momentum の骨格を含む）。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計して検証レポートを生成する CLI。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均 / 最大 / P95）を計算し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタのサポート、DB 存在チェックとエラーハンドリングを実装。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- （初回リリースにつき該当なし）

---

注記:
- 上記はソースコードから推測してまとめた変更履歴です。実際のリリースノート作成時は、コミット履歴・リリース日付・影響範囲（例: 既存ユーザ向けの移行手順・互換性破壊の有無）をプロジェクトの実状に合わせて調整してください。