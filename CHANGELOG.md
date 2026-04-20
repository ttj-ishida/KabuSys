# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載します。  
リリース日はコードベースの現在日付（2026-04-20）を使用しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じてブローカークライアントを選択（paper_trading では MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグファイル（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）をサポート。
    - リスク管理用デフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を構成して起動。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグ検知で安全にループを終了し、例外はログに出力して次ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env ファイル読み込み時の挙動:
      - `export KEY=val`、シングル/ダブルクォート、エスケープ、行内コメントなど多くのケースに対応するパーサーを実装。
      - OS 環境変数は保護（上書きを制御）。
    - Settings クラスを実装し、環境変数をプロパティ経由で取得:
      - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（instant/partial/never/reject）などの検証
      - 各種閾値（CPU/MEM/DISK）、PID/KILL フラグパス、ログレベル、実行環境判定（development/paper_trading/live）等

  - config_setup.py
    - 対話式 .env ウィザードを実装。
    - 既存 .env の読み込み・編集、シークレット値のマスク表示、保存前の確認提示を行う。
    - 保存時にはテンプレートヘッダ付きで .env を作成。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL 検証、DB パスの存在チェック（親ディレクトリ）、config/*.yaml の存在・パース検証（PyYAML がある場合）を実施。
    - KABUSYS_ENV=live 時の安全ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ユーティリティ
  - logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数で設定解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron/Task Scheduler での扱いを簡便化。
  - process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応 OS の場合は警告をログに出してスキップする安全設計。

- Portfolio 構成モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（score 降順 tie-breaker: signal_rank）: select_candidates
    - 等金額配分: calc_equal_weights
    - スコア加重配分: calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有に基づき特定セクターの新規候補を除外するロジックを実装。unknown セクターは除外対象外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対応し、未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）: allocation_method ("risk_based", "equal", "score") に対応。
    - risk_based: リスク許容率と損切り率から理論株数を算出し単元株（lot_size）で丸める。
    - aggregate cap（available_cash）を超えた場合はスケールダウンと残差処理で lot 単位の追加配分を行う。
    - max_position_pct、max_utilization、cost_buffer 等を考慮。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH / --db オプション）から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from/--to）に対応。

- リサーチ（基礎）
  - research/factor_research.py（実装開始）
    - ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。momentum の計算関数（calc_momentum）などを実装開始（注: ソース一部に未完の箇所あり）。

### 変更 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### 削除 (Removed)
- N/A（初回リリース）

### 非推奨 (Deprecated)
- N/A（初回リリース）

### セキュリティ (Security)
- N/A（初回リリース）

---

注:
- 本 CHANGELOG はコードから推定して作成しています。実装の細部（例: BrokerClientFactory の具体的なブローカー選定、SystemMonitor の内部実装、ExecutionEngine/Reconciler の振る舞い等）は省略していますが、上記に列挙したインターフェースや主要仕様はソースコードから読み取れる通りです。