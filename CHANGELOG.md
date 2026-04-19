# CHANGELOG

すべての注目すべき変更をこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム KabuSys の基本モジュール群を追加しました。

### Added
- 実行エントリ・監視エントリ
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止管理用のフラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - BrokerClientFactory によりブローカークライアントを抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行スレッド化を実装。
    - RiskManager 初期設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を採用。initial_portfolio_value は broker.get_available_cash() を用いて決定。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` により上書き可能。無効値（非正の値や整数でない値）はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関係なく本番用の sqlite_path を使用して初期化（init_monitoring_db を呼び出し）。
    - duckdb を分析用に接続。
    - 停止フラグ検知でループを終了（data/stop_requested.flag）。
    - check_once() 実行時の例外をキャッチしてログに出力し、次ポーリングまで継続。

- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local の自動読み込みを実施（OS 環境変数は保護）。
    - .env パース実装: export 前置、クォート文字列、インラインコメントなどに対応。
    - Settings クラス: 各種設定値をプロパティで取得（J-Quants, kabuAPI, LINE, DB パス, PID/kill flag パス, モニタ閾値, env/log level 判定等）。
    - PAPER_FILL_MODE のバリデーション、有効値: "instant" / "partial" / "never" / "reject"。
    - KABUSYS_ENV/LOG_LEVEL のバリデーション（不正値は ValueError）。

  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。
    - 対話入力、既存 .env 読み込み、シークレットマスク表示、選択肢チェック、保存確認を実装。
    - 保存時にテンプレート形式で .env を出力（.env を絶対にコミットしない旨のヘッダを含む）。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の未設定/プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パースチェック（PyYAML 未インストール時は警告でスキップ）を実施。
    - --strict オプションで警告もエラー扱いにするモードを提供。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定するユーティリティを追加。
    - 既存ハンドラをクリアしての再初期化、ログディレクトリ解決（LOG_DIR 環境変数優先）、ログレベル解決順（引数 > LOG_LEVEL > INFO）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority(level) で "high" / "normal" / "low" を指定可能。権限不足などで失敗した場合は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（利用可能コア数より大きい指定は全コア使用にフォールバック、エラー時は警告を出力）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックして警告。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の適用（既存保有のセクター別時価で判定）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告を出して 1.0 を返す。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた株数算出を実装。
    - 単元株（lot_size）丸め、per-stock 上限（portfolio_value * max_position_pct）、aggregate cap（available_cash）を実装。
    - cost_buffer を考慮した保守的見積り、スケーリング後の残差配分ロジックを追加。
    - 価格欠損時のスキップ処理やログ出力を実装。

- 解析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）からデータを集計し、稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) などの指標を算出してレポートを標準出力に出力。
    - デフォルトの合格基準を定義（稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms）。
    - 日付範囲フィルタ（--from, --to）と --db オプションをサポート。
    - 空データやテーブル未存在時に耐性を持たせて N/A などで表示。

- 研究用モジュール（途中実装）
  - research/factor_research.py:
    - DuckDB と prices_daily / raw_financials テーブルを用いたファクター計算の骨組みを追加（モメンタム、MA200乖離、ATR、流動性等）。関数 calc_momentum の導入と定数定義を含む（実装は継続中）。

### Changed
- なし（初回リリースにつき該当なし）。

### Fixed
- なし（初回リリースにつき該当なし）。

### Notes / Implementation details
- 設定自動読み込み:
  - デフォルトで .env/.env.local を自動読み込み（プロジェクトルートを .git または pyproject.toml から判定）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - .env.local は OS 環境変数を保護しつつ .env を上書きできるように実装。
- DB 初期化:
  - run_execution と run_monitoring は init_monitoring_db を呼び出して監視テーブルの存在を担保（冪等に動作）。
- ログ:
  - コンソール出力には stdout を使用（cron や外部監視ツールで stdout/stderr をまとめやすくするため）。
  - ログファイルの作成に失敗しても、コンソールログは必ず維持されるよう堅牢化。
- エラーハンドリング:
  - 監視ループやレポート生成等は、テーブル未存在や OperationalError に対して耐性を持ち、可能な限り情報を出力して継続する設計。
- セキュリティ/運用注意:
  - .env の取り扱いに関する注意喚起を config_setup で出力（.env を絶対に Git にコミットしない）。
  - validate_config により本番環境（KABUSYS_ENV=live）時の重要なガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START 設定）を警告。

---

以上。今後の変更はこのファイルに時系列で追記してください。