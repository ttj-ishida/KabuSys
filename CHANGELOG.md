# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングに基づいて記録しています。  

※ 日付はこのリリース作成時点です。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース — 基本的な実行/監視ツール、設定管理、ポートフォリオ構築、ユーティリティ、解析ツールを実装。

### Added
- コア情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の `data/stop_requested.flag` によるフラグ検知で行う。
    - 監視は常に本番用の sqlite_path を使用して初期化。
    - プロセス優先度を上げる（`set_process_priority("high")`）および統一ログ設定を使用。
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading DB を使用（`data/paper_trading.db` がデフォルト）し、MockBrokerClient を利用する想定。
    - 停止フラグの検知・エンジン停止、PID ファイル管理、スレッドでの実行制御を実装。
    - 起動時にプロセス優先度を上げる（`high`）。

- 設定管理
  - config.py: 環境変数/ .env の読み込み・ラッパー `Settings` を実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により .env を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` ファイルのパースはクォート、エスケープ、コメント処理に対応。
    - DB パス、Paper Trading 周り（`paper_sqlite_path`、`paper_fill_mode`）や閾値（CPU/MEM/DISK）等のプロパティを提供。
    - 環境値バリデーション（`env`、`log_level` 等）。
  - config_setup.py: 対話式 `.env` ウィザードを追加。
    - 既存 `.env` の読み込み、シークレットのマスク表示、対話入力、保存機能を提供。

- 設定検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検証（PyYAML 利用可）、本番環境用の追加ガード等を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選出、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重。スコア全体が 0 の場合は等配分にフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用するフィルタ機能。既存保有のセクター暴露を計算し上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数算出ロジックを実装。
      - allocation_method に応じた振る舞い（risk_based / equal / score）。
      - lot_size（単元）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン（cost_buffer を考慮）。
      - 利用可能現金に対するスケールと端数処理（残余キャッシュで fractional 残差の大きい順に lot を付与）を実装。

- ユーティリティ
  - utils.logging_setup: ログ設定ユーティリティを追加。
    - StreamHandler を stdout に設定（cron 等で stdout/stderr をまとめる運用を想定）。
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/ ディレクトリ、30 日保持）。
    - 既存ハンドラのクリア処理、LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度・CPU affinity の簡易ユーティリティを追加。
    - Windows と POSIX（Linux/macOS/FreeBSD）を吸収する実装。`set_process_priority` と `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS の場合は警告を出し安全にスキップ。

- 監視/モニタリング
  - monitoring_db 初期化呼び出し（起動スクリプトから呼ばれる形で、監視テーブルが存在することを保証する冪等初期化）。
  - SystemMonitor を利用した一回チェック (check_once) をループで実行（例外はログ出力して次回へ）。

- Execution コンポーネント初期設定
  - Execution 側の依存組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の呼び出し・デフォルトパラメータを実装。
  - RiskManager のデフォルト設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）を設定し、初期ポートフォリオ値をブローカーから取得。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading DB（`PAPER_TRADING_SQLITE_PATH` で指定）から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数等を集計。
    - 合否基準（デフォルト閾値）を設定：稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 latency <= 200ms。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
    - P95 計算と欠損データの安全ハンドリングを実装。

- リサーチ（未完）
  - research.factor_research: ファクター計算モジュールの雛形を追加（モメンタム／MA200／ATR 等を想定）。
    - コードの一部（calc_momentum の冒頭）を実装中（未完の末尾あり）。

### Changed
- （初回リリースのため "Changed" は該当なし）

### Fixed
- （初回リリースのため "Fixed" は該当なし）

### Removed
- （初回リリースのため "Removed" は該当なし）

### Notes / 補足
- .env パーサはシングル/ダブルクォートやバックスラッシュによるエスケープ、インラインコメントの扱いなど細かく実装しているため、従来の単純なパーサより堅牢です。
- run_execution/run_monitoring はプロセス優先度設定と統一ログ設定を共通で利用する設計になっており、運用時にログ出力先や優先度の調整が容易です。
- Paper Trading（ペーパートレード）は本番 DB と完全に分離される設計（専用 sqlite ファイル）で、実運用への影響を避けるようになっています。
- research.factor_research の実装は継続中のため、完全なファクター計算は次リリースで追加予定。

---

（今後のリリースでは各ファイル/機能単位でより細かい変更履歴、互換性注記、マイグレーション手順などを追加していきます。）