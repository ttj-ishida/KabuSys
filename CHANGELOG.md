# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

> なお、本リリースノートはコードベースの実装内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成とコマンドラインエントリを実装
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数から設定を取得する `kabusys.config.Settings` を実装。
  - .env ファイルの自動読み込み機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。  
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ファイルパーサは `export KEY=val` 形式、シングル/ダブルクォート、インラインコメントの処理に対応。
  - 各種設定プロパティを提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`, `PID_FILE_PATH`, CPU/MEM/DISK の閾値 等）。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話的ウィザードを実装。`.env` の初期作成/更新を支援。
  - ウィザードは既存 .env の読み込み、入力プロンプト、シークレットのマスク表示、確認後に `.env` を書き込む機能を持つ。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パスの検証、config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）や本番環境向けのガードチェックを行う。
  - `--strict` オプションで警告を失敗として扱い exit(1) を返す。

- 実行/監視エントリポイント
  - ExecutionEngine 起動スクリプト `kabusys.run_execution` を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は Paper 用専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - `BrokerClientFactory` 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine` をスレッドで起動。停止フラグ (`data/stop_requested.flag`) を監視して安全に停止可能。
    - デフォルトの RiskManager 設定を含む（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20, initial_portfolio_value=broker.get_available_cash()）。
  - SystemMonitor ポーリングループ起動スクリプト `kabusys.run_monitoring` を実装。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path`（デフォルト `data/monitoring.db`）を使用。
    - 停止フラグ `data/stop_requested.flag` を検知して安全にループを終了する。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。

- DuckDB / SQLite の利用
  - DuckDB（デフォルト `data/kabusys.duckdb`）と SQLite をデータアクセス用に併用。各モジュールは接続を受け取って処理を行う。

- プロセスユーティリティ
  - `kabusys.utils.process_priority` に process 優先度設定機能を実装。
    - Windows（`psutil` の優先度定数）と POSIX（nice 値）を吸収。未対応 OS はスキップしログ出力。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を実装。
    - アクセス権限や未サポート API の失敗を警告しつつ安全にスキップ。

- ポートフォリオ建設（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`、等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装。
    - スコアが全て 0 の場合は等配分にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限を適用する `apply_sector_cap`（既存保有のエクスポージャ計算、売却予定銘柄の除外対応、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull":1.0、"neutral":0.7、"bear":0.3、未知は 1.0 にフォールバックして警告）。
  - `kabusys.portfolio.position_sizing`
    - 複数の配分方式に対応した株数計算 `calc_position_sizes`（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した保守的見積り、残余キャッシュによる端数配分ロジック等を実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` にモメンタム／ボラティリティ等のファクター計算を実装（DuckDB の prices_daily テーブルを使用）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - ボラティリティ: ATR、相対 ATR、20 日平均売買代金、出来高比 等（関数は DuckDB SQL を利用して計算）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装。Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）からレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等を集計。
    - P95 の計算、期間フィルタ（--from / --to）、閾値による PASS/FAIL 判定（稼働率 >= 99%、fill_rate >=90% 等）を実装。
    - DB 存在チェックとテーブル欠如時のフォールバック（N/A 表示）。

### Changed
- 起動時のプロセス優先度設定を開始シーケンスの早い段階で行うように変更（run_monitoring/run_execution）。これにより重要プロセスのスケジューリングを安定化。

### Fixed
- MONITOR_POLL_INTERVAL の取り扱いで 0 以下や非整数入力に対して ValueError を避けるためにフォールバック実装を追加（警告ログ出力）。
- .env パーサ周りの振る舞いを強化し、クォート内のエスケープやインラインコメント処理の誤解釈を防止。

### Security
- .env の取り扱いに関する注意喚起を config_setup の出力ヘッダに追加（.env を絶対に Git にコミットしない旨）。
- 設定検証で本番環境（KABUSYS_ENV=live）時に通知トークン未設定や KILL フラグの自動クリア設定等の危険を警告。

---

参考: 実装済みの主な環境変数とデフォルト値（抜粋）
- KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (default: 60)
- KILL_FLAG_CLEAR_ON_START (default: 0)
- PAPER_FILL_MODE (default: instant) — 有効値: instant | partial | never | reject
- LOG_LEVEL (default: INFO)

もし CHANGELOG に追加したいリリース日付や分類（Breaking changes など）を変更したい場合は指示してください。