# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを前提とします。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- プロジェクト初版リリース。
- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを提供。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。エンジンはスレッドで実行し、停止フラグ（data/stop_requested.flag）で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から設定値を取得する統一インターフェースを提供。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env の行パーサーを実装（export 形式、クォート文字列、エスケープ、インラインコメントの扱いに対応）。
    - 必須項目取得用 _require()、各種パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH 等）、監視しきい値（CPU/MEM/DISK）やログレベル、環境名（development/paper_trading/live）などをプロパティ化。
    - PAPER_FILL_MODE（paper trading の fill モード）のバリデーション（有効値: instant/partial/never/reject）。
    - Settings インスタンスをモジュール単位で提供（settings）。

- 設定検証・セットアップ CLI
  - validate_config.py
    - .env と config/*.yaml の起動前検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML があればパース検証を実行。
    - KABUSYS_ENV=live 時のガードチェック（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - 主な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話形式で入力・保存可能。
    - 保存時に簡易確認を表示し、.env をテンプレート形式で書き出す（.env を Git にコミットしないよう注意コメント付き）。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging() を実装。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリは引数 > LOG_DIR > デフォルト "logs" の順で解決。ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - ログレベルは引数 > LOG_LEVEL > "INFO" の順で解決。
  - utils/process_priority.py
    - set_process_priority(level: "high"|"normal"|"low") を実装。Windows と POSIX（Linux/Mac/FreeBSD）で適切な優先度設定を行い、対応外 OS や権限不足時は警告してスキップ。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は設定しない）。権限不足や未サポート環境では警告してスキップ。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio/portfolio_builder.py
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャが max_sector_pct を超える場合、当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
    - risk_based: risk_pct と stop_loss_pct に基づくポジションサイジング。
    - equal/score: ウェイトに基づく配分。各ポジションに対する max_position_pct、全体での max_utilization を考慮。
    - 単元株（lot_size）で丸め、cost_buffer による保守的コスト見積りを考慮した aggregate cap スケーリングと余剰配分アルゴリズムを実装。
    - 価格欠損や価格 <= 0 の場合は該当銘柄をスキップ。将来的なフォールバック価格の注記あり（TODO）。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した paper trading DB を解析して稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を計算し PASS/FAIL を出力。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ --from / --to をサポート。P95 は内部でソートして算出。

- research/factor_research.py（ファクター計算の骨格）
  - DuckDB 接続を受けて prices_daily / raw_financials から Momentum/Value/Volatility/Liquidity 系ファクターを計算する設計を開始（モメンタム等の定数・仕様記載、calc_momentum の仕様コメントあり。実装は途中まで存在）。

### 変更 (Changed)
- （初期リリースにつき該当なし）

### 修正 (Fixed)
- （初期リリースにつき該当なし）

### 非推奨 (Deprecated)
- （初期リリースにつき該当なし）

### 削除 (Removed)
- （初期リリースにつき該当なし）

### セキュリティ (Security)
- （初期リリースにつき該当なし）

Notes / 備考
- 多くの機能は純粋関数（DB 参照なし）として設計され、単体テストがしやすい構造を目指しています。
- run_monitoring / run_execution の挙動はファイルベースの停止フラグ (data/stop_requested.flag) や PID ファイル (data/execution.pid) に依存します。運用時は data ディレクトリの権限と存在を確認してください。
- .env は機密情報を含むため絶対に VCS にコミットしないでください（config_setup が生成する .env にはその旨の注意を記載しています）。
- 将来的な改善点として、position_sizing の lot_size を銘柄毎に持たせる、price のフォールバックロジック、research モジュールのファクター計算完成などが想定されています。