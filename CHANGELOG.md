CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
凡例: Added, Changed, Fixed, Deprecated, Removed, Security

Unreleased
----------

- なし

[0.1.0] - 2026-04-25
--------------------

Added
- 基本アプリケーション初期リリース。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
- 起動スクリプト群を追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 停止はプロジェクト data/stop_requested.flag によるフラグ検知で行う。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用する仕様。
    - sqlite3 / DuckDB に接続し、監視用 DB 初期化を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（data/paper_trading.db をデフォルト）を使用し、MockBroker を介した分離されたペーパートレードが可能。
    - 起動時に process priority を "high" に上げる。
    - 停止フラグ（data/stop_requested.flag）を監視し、検出時にエンジン停止を試みる。PID ファイル出力に対応。
- 設定管理・ヘルパー:
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env/.env.local の読み込み順と上書きポリシーを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
    - 複数の Settings プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
  - config_setup.py
    - 対話式 .env ウィザードを実装。既存 .env の読み込み・編集、デフォルト値提示、シークレットマスク、保存機能を提供。
  - validate_config.py
    - 起動前設定検証 CLI を実装（--strict オプションで警告を失敗扱いにできる）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）。
    - 本番環境用の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
- ロギング/プロセスユーティリティ:
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を実装。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続する堅牢性を実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定を実装（Windows / POSIX に対応）。set_cpu_affinity も提供（利用不可時は警告でスキップ）。
    - アクセス権限不足等の例外は警告として扱い起動継続。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で BUY シグナルを選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックし警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック。既存ポジションのセクター別エクスポージャー計算に基づき、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分を実装。lot_size（単元株）丸め、1 銘柄上限（max_position_pct）、アグリゲート上限（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差を用いた追加配分ロジックを実装。
- 取引検証ツール:
  - tools/paper_verification_report.py
    - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、PASS/FAIL 判定を行うレポートを実装。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - --from/--to/--db オプションをサポート。
- 研究用モジュール:
  - research/factor_research.py（モメンタム等のファクター計算用の骨組みを追加）
    - DuckDB の prices_daily / raw_financials を使ったモメンタム、MA、ATR、出来高等のファクター計算設計を開始。関数 calc_momentum() の骨組みを実装（ファイル末尾は一部切れているが、設計方針と定数が定義済み）。
- データベース初期化:
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び出し、監視用テーブルが存在することを保証（冪等）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Notes / Implementation details
- .env パーサはシングル/ダブルクォート内のエスケープや inline コメントの取り扱い、"export KEY=val" 形式に対応。
- 設定読み込みは OS 環境 > .env.local > .env の優先順位。テスト等で自動ロードを無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- Logging は stdout を利用する設計のため、cron/task scheduler などで stdout/stderr を一本化してリダイレクトしやすくしている。
- run_execution のリスク管理デフォルト値（RiskConfig）や ExecutionEngine の初期化はソース内に具体的な初期値を含む（例: max_position_pct=0.20, max_utilization=0.80 等）。
- run_monitoring は例外をキャッチしてログに残しつつポーリングを継続する堅牢なループ実装。

開発者向けメモ
- research/factor_research.py は未完の箇所があり（ファイル末尾が途中）、実際のファクター計算ロジックの完成が必要。
- 将来的な拡張案として、position_sizing の lot_size を銘柄別に対応する（stocks マスタから lot_map を受け取る）設計変更が検討されている（TODO コメントあり）。