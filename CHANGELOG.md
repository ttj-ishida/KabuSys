# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初回リリース。
- 環境設定 / 起動用スクリプト
  - config.Settings: 環境変数ベースの設定読み取りクラスを追加。
    - J-Quants / kabuステーション / LINE / DB パス / 各種閾値 / 実行環境（development/paper_trading/live）などのプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実施。
    - PAPER_FILL_MODE（paper_trading 用の fill_mode）を検証。
    - paper_sqlite_path, pid_file_path, kill_flag_path 等のパスを管理。
  - config ファイル自動読み込み機能
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロード（OS 環境変数は保護）。
    - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - config_setup.py: インタラクティブな .env 作成・更新ウィザードを追加。
    - 必須/任意項目、シークレット入力、既存値の再利用、.env ファイル出力をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ、config/*.yaml の存在と YAML パース（PyYAML がある場合）等をチェック。
    - --strict モードで警告を失敗扱いにできる。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモンスレッドで実行。停止フラグファイル（data/stop_requested.flag）で停止可能。
    - PID ファイル管理（data/execution.pid）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path（monitoring DB）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。停止は stop_requested.flag による。
    - SQLite / DuckDB 接続の初期化処理を実行（init_monitoring_db）。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging:
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler, 30日保持）のファイルハンドラをルートロガーに設定。
    - LOG_LEVEL/LOG_DIR の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度 (nice / priority class) を設定。失敗時は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity 固定をサポート（許可されない場合は警告で継続）。
- ポートフォリオ構築関連モジュール（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank を採用）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア重み配分（全スコア 0 の場合は等分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外するロジック。unknown セクターは無視。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を算出。lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer による保守的コスト見積もり、残余キャッシュによる再配分ロジックを実装。
    - risk_based 方式では risk_pct や stop_loss_pct を用いてベース株数を計算。
    - 未取得価格や price <= 0 の銘柄はスキップし、ログ出力で通知。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（system_status）、注文成功率 / 送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（avg/max/P95）。
    - P95 計算、期間フィルタ、複数の OperationalError 耐性（テーブル未存在時のフォールバック）を実装。
    - デフォルトの合格基準 (稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200 ms) に基づき PASS/FAIL を判定。
- 研究用モジュール（部分実装）
  - research.factor_research: DuckDB 接続を受け取りファクター（Momentum/Value/Volatility/Liquidity）を計算する骨組みを追加。モメンタム計算等の定数と関数の雛形を実装（ファイル末尾で実装途中）。

### Changed
- N/A（初回リリースのため、過去バージョンからの変更履歴はありません）。

### Fixed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

---

注意事項 / 実装上の備考
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊環境では自動ロードがスキップされる可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_monitoring は設計上「監視専用 DB（monitoring.db）」を本番パスで使用します。環境に依らず本番監視 DB を参照する点に注意してください。
- run_execution は paper_trading モードで paper_trading 用 DB を使用するため、本番データと分離できますが、設定ミスによる DB の参照先混在が起きないよう .env の確認を推奨します（validate_config を使用）。
- process_priority / cpu_affinity はプラットフォーム依存で動作しない場合があり、アクセス権限不足等で設定に失敗した場合は警告ログが出ますが処理自体は継続します。
- portfolio モジュールは「純粋関数」として設計されており、外部副作用はありません。単体テストが容易な設計です。
- research.factor_research はまだ実装途中の関数（ファイル末尾で途中）があります。必要な場合は追加実装してください。

バージョン情報
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

もし追加でリリースノートを拡張したい点（例えば機能の優先度、既知の問題、互換性注意点など）があれば指示してください。