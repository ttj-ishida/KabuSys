# Changelog

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般
- パッケージ名: KabuSys
- 現行バージョン: 0.1.0
- リリース日: 2026-04-18

Unreleased
- （なし）

[0.1.0] - 2026-04-18
----------------------------------------

Added
- 初期リリース。日本株自動売買システム KabuSys の基礎機能群を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ file (data/stop_requested.flag) を検知してループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、Engine のデーモン実行と停止フラグ検知を実装。
    - 実行中の PID 管理（data/execution.pid）と停止フラグによる安全停止をサポート。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する API を提供。
    - .env 自動読み込み機能: プロジェクトルートの .env を読み込み、.env.local で上書き（既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値、env/log_level 判定等）を提供。PAPER_FILL_MODE の値検証あり。
    - settings = Settings() のインスタンスをエクスポート。
- 設定ユーティリティ／CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 入力の既存値再利用、シークレット項目マスク、デフォルト値・選択肢対応などの UX を持つ。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DUCKDB/SQLITE パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML があればパース検証）を行う。
    - KABUSYS_ENV=live の場合の追加警告（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング／プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、LOG_DIR/LOG_LEVEL からの上書き対応。既存ハンドラの重複設定防止処理あり。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil ベース）。
    - Windows / POSIX の差分吸収、アクセス権限・非対応環境でのフォールバックと警告出力を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）および重み算出（calc_equal_weights, calc_score_weights）を追加。
    - score が全て 0 の場合は等分配にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存保有のセクター比率が max_sector_pct を超える場合、新規候補を除外）。"unknown" セクターは除外対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull":1.0, "neutral":0.7, "bear":0.3、未知は 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing（calc_position_sizes）を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size, デフォルト 100）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリングアルゴリズムを実装。コストバッファ（cost_buffer）を反映。
    - risk_based モードでは risk_pct / stop_loss_pct を用いて基準株数を算出。
- リサーチ（ファクター計算）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加。duckdb 接続を受け、prices_daily / raw_financials を参照してモメンタム・バリュー・ボラティリティ・流動性等の計算を行う設計。
    - 各種定数（期間・ウィンドウ長）と calc_momentum のインターフェースを定義。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。閾値はソース内定義（例: 稼働率 >= 99.0% 等）。
    - --from / --to / --db オプションをサポート。
- その他
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 監視テーブルの初期化: init_monitoring_db 呼び出しを追加し、監視テーブルの存在を保証（冪等操作）。

Changed
- （初期リリースにつき該当なし）

Fixed
- ログハンドラの二重登録防止、ファイル出力失敗時のフォールバックなど起動時の頑健性向上（logging_setup の設計に含む）。
- run_execution/run_monitoring で監視 DB のテーブルが存在することを確実にするため init_monitoring_db を呼び出すようにした。

Security
- 環境変数読み込み時のシークレット項目扱い（config_setup のマスク表示）と .env の Git コミット回避の注意喚起を追加。

Notes / Known behaviors / Design decisions
- run_monitoring は KABUSYS_ENV に依存せず、常に settings.sqlite_path（本番向け monitoring.db）を使用します。モニタリングデータを本番 DB に集約する設計です。paper_trading の隔離が必要な場合は設定で sqlite_path を変更してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（data/paper_trading.db）を使用して発注履歴を分離します。
- .env 自動ロードはプロジェクトルート検出（.git または pyproject.toml）に依存します。自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority や CPU affinity の設定は権限やプラットフォーム依存で失敗することがあるため、安全にスキップして警告を出力する実装になっています。
- position_sizing の集約スケーリングは lot_size 単位での丸め・残差配分ロジックを持ち、available_cash を超えないように調整します。

参考: 主要 CLI / エントリ
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution
- python -m kabusys.config_setup
- python -m kabusys.validate_config [--strict]
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の予定（非包含）
- research/factor_research の完全実装（全ファクター算出・正常系のテスト）
- strategy / execution モジュールの詳細実装、単体テストの追加
- ロギング・メトリクスのさらなる強化と監視ダッシュボード連携

---  
（以上）