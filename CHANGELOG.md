# Changelog

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を利用したデータ処理基盤を導入（デフォルトパス、環境変数による上書き対応）。

- 設定関連
  - Settings クラスを実装（kabusys.config）
    - 環境変数経由で各種設定を取得（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境など）。
    - KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
    - paper_fill_mode の妥当性チェック（instant / partial / never / reject）。
    - paper_sqlite_path, duckdb_path, sqlite_path 等の Path を返すプロパティを提供。
  - 自動 .env ロード機能を実装
    - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数の保護（override の取扱い）に対応。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い等に対応）。

- 設定ツール / 検証
  - 対話式設定ウィザードを追加（kabusys.config_setup）
    - .env の初期作成 / 更新を支援。各項目の説明・デフォルト・シークレット入力をサポート。
  - 設定検証 CLI を追加（kabusys.validate_config）
    - 必須環境変数・KABUSYS_ENV 値・LOG_LEVEL・DB パスの基本検証。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - 本番環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）
    - 実行に必要なコンポーネントを組み立てて ExecutionEngine を起動（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler）。
    - paper_trading 環境では paper_sqlite_path を用いて本番 DB と完全分離。
    - エンジンを別スレッドで実行し、 data/stop_requested.flag による停止検知で優雅に停止。
    - data/execution.pid に PID を管理する設計を導入（pid_file の取り扱い）。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）
    - SystemMonitor を用いたポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず production の sqlite_path を利用する仕様（監視データは本番DB想定）。
    - stop flag による停止、例外発生時のログとループ継続を考慮。

- 実行ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）
    - set_process_priority(level) — Windows / POSIX を吸収して nice / priority を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定（未対応環境や権限不足は警告でスキップ）。
    - run_execution / run_monitoring 起動時にデフォルトで優先度を "high" に設定する運用に。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。
    - calc_equal_weights, calc_score_weights: 等配分／スコア加重（スコア合計が 0 の場合はフォールバックで等配分）。
  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金 multiplier（bull/neutral/bear → 1.0/0.7/0.3、未知は警告して 1.0 にフォールバック）。
    - 注意点として、価格欠損時の将来的なフォールバックの TODO コメントを残す。
  - 株数決定・リスク制限（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算。
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリング処理を実装。
    - 可用性不足時のスケールダウンロジック（残差の分配ロジック）を実装。

- リサーチ / ファクター計算
  - factor_research モジュールを追加（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB(SQL) ベースで計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等を計算（データ不足時は None を返す）。
    - DuckDB を使ったウィンドウ関数ベースの実装、スキャン範囲のバッファを設定。

- 検証ツール
  - Paper Trading 検証レポートを追加（kabusys.tools.paper_verification_report）
    - paper_trading の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を集計してレポート出力。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ 等。
    - デフォルトの合格閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ (--from / --to)、--db オプション対応。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_execution / run_monitoring の起動時に実行し、監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / Notes
- apply_sector_cap:
  - "unknown" セクターは上限判定の対象外となるため、マスタにセクター情報が欠けていると上限回避される可能性あり（TODO: フォールバックロジック検討）。
- calc_score_weights:
  - 全銘柄のスコアが 0 の場合は等金額配分へフォールバックし、WARNING を出力する実装。
- process_priority / set_cpu_affinity:
  - 権限不足やプラットフォーム非対応時は警告を出して処理をスキップする振る舞い。
- run_monitoring:
  - 監視は環境にかかわらず sqlite_path（本番想定）を使用するため、paper_trading と監視 DB を分離したい場合は設定の見直しが必要。
- .env 自動読み込み:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする（テスト等での isolation を容易にするため）。
- 一部の YAML 検証は PyYAML 未インストール時にスキップされ、警告を出力する。

### Environment variables (主なもの)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD （必須）
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔（秒）)
- KILL_FLAG_CLEAR_ON_START (0/1)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動ロード無効化)

---

注: 将来的なリリースではバグ修正、パフォーマンス改善、外部依存の抽象化（broker クライアントの拡張、lot_size の銘柄別対応など）を予定しています。