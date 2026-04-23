# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-23

初回公開リリース。

### 追加
- 基本パッケージ構成を追加（kabusys パッケージ）
  - バージョン: `__version__ = "0.1.0"`

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視では環境にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）の検知でループ終了。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時はペーパー用 DB（data/paper_trading.db を想定）と MockBrokerClient を使用し、本番 DB と分離。
    - 停止フラグ検知でエンジン停止。PID ファイル管理（data/execution.pid）。
    - プロセス優先度を起動時に "high" に設定。

- 設定・環境管理
  - config.py
    - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパース機能：コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
    - Settings クラスを導入：環境変数から設定を提供（DB パス、API トークン、Paper Trading 切替、監視閾値、PID/Kill flag パスなど）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
    - ログレベル検証（DEBUG/INFO/...）。

  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを実装。
    - デフォルト値・選択肢・シークレット入力・既存 .env 読み込みをサポート。
    - .env ファイル書き出しテンプレートを提供（.env を絶対にコミットしない旨の注記を含む）。

  - validate_config.py
    - 起動前の設定検証 CLI を提供（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在/パース、live 時の追加ガードをチェック）。
    - --strict オプションで警告も失敗扱いに可能。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等金額へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）：既存保有のセクター比率が上限を超える場合、新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）：bull/neutral/bear をマップ。未知レジームは 1.0 にフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - position sizing ロジック（calc_position_sizes）を実装。
    - allocation_method ("risk_based", "equal", "score") をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）チェック、cost_buffer による保守的見積り、スケールダウンと端数処理（残余キャッシュでの配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を集計しレポートを生成する CLI を追加。
    - 取得指標:
      - システム稼働率（system_status）
      - 注文成功率 / 送信率（trade_logs の Created / Filled / Sent）
      - リスク却下数（risk_logs）
      - レイテンシ（avg, max, P95）
    - P95 計算実装。期間フィルタ（--from / --to）をサポート。
    - 判定基準（閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB ファイルが見つからない・テーブル欠如時に適切に N/A やデフォルトを表示。

- research/factor_research.py（ファクター計算の骨組み）
  - DuckDB 接続を用いたモメンタム等のファクター計算モジュールを追加（設計・定義、関数シグネチャと定数を実装。モジュール途中まで実装）。
  - モメンタム、MA200、ATR、出来高系などの計算を行う設計方針を明記。

### 仕様（主な環境変数・デフォルト）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト: 60）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

### 既知の注意点
- config 自動ロードはプロジェクトルートが検出できない場合スキップされる（.git または pyproject.toml を基準に探索）。
- process_priority の一部操作は権限（管理者/root）が必要な場合があり、失敗時はログで警告してスキップする。
- logging_setup はログディレクトリ作成に失敗するとファイル出力を無効化しコンソール出力にフォールバックする。
- research/factor_research.py はファイル末尾で未完の実装が見られます（更なる実装が必要）。

### 破壊的変更
- 初版のため該当なし。

-- End of CHANGELOG --