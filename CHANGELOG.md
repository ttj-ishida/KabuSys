CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
日付は本リリース作成日です。

[Unreleased]
-------------

- なし

0.1.0 - 2026-04-18
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
- 実行用スクリプト / デーモン類を追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 停止はプロジェクトルートの data/stop_requested.flag によるファイルフラグで行う。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用し、duckdb も併用して初期化。
    - check_once() 実行中の例外はキャッチしてログ出力し、ループは継続する安全設計。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient（BrokerClientFactory 経由）と paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行時の PID を data/execution.pid に保持する仕組み（PID ファイル経路は設定で指定可能）。
- 設定管理機能を追加
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 強力な .env パーサを実装（export プレフィックス、クォート文字列、エスケープ、インラインコメント処理などに対応）。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等の設定プロパティを提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）などの値検証を実装。無効な値は ValueError を送出。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
    - settings = Settings() をモジュールレベルで提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - 既存 .env の読み込み、シークレットマスク表示、デフォルト提示、バリデーション（選択肢）等に対応。
    - 最終確認プロンプトの後に .env を出力。書式はテンプレートに従う（.env を絶対に Git にコミットしない旨の注記を含む）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の問題を検出する検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV の値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告（LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から各種検証指標（稼働率 / 注文成功率 / 送信率 / P95 レイテンシ / リスク却下数 等）を算出しレポート化する CLI を提供。
    - --from / --to / --db オプションに対応。DB が存在しない場合はエラーメッセージを出力して終了。
    - 閾値に基づく PASS/FAIL 判定を実装（稼働率 99%、注文成功率 90% など）。
- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークの実装。
    - calc_equal_weights: 等配分。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等配分にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは 1.0 にフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき各銘柄の発注株数を算出。lot_size（単元）で丸め、per-stock 上限・aggregate 上限（available_cash）を考慮。スケーリング時の再配分ロジック（端数処理）を実装。
  - portfolio/__init__.py により上記主要関数をエクスポート。
- ユーティリティを追加
  - utils/logging_setup.py
    - setup_logging 関数を実装。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 世代保存）を設定。
    - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/ の順で解決。作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト INFO の順で解決。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows と POSIX（Linux/Mac 等）で差分を吸収。psutil を利用して優先度設定や CPU affinity 固定を行う。権限不足や未対応 OS の場合は警告を出してスキップ。
- その他
  - monitoring.monitoring_db.init_monitoring_db を実行して監視用テーブルの存在を保証（冪等）。
  - 多くの箇所で例外処理を採用し、起動時やループ中の致命的でない失敗をログ化して継続する堅牢性を確保。
  - パッケージ内ツール・モジュールの __init__ ファイルを整備。

Changed
- 初期リリースのため履歴なし。

Fixed
- 初期リリースのため履歴なし。

Security
- 初期リリースのため履歴なし。

Notes / Known issues
- research/factor_research.py はモメンタム等ファクター計算の骨組み（定数、関数定義開始）を実装済みですが、ファイル末尾が切れており一部実装が未完（calc_momentum の内部実装の続きが途中）です。今後のリリースで完成予定。
- 一部の TODO コメント（例: position_sizing における銘柄別 lot_size 拡張、price フォールバック戦略など）が残っています。
- .env 自動読み込みの挙動は、OS 環境変数を保護するため .env.local の上書きでも既存 OS 環境変数は上書きされません。自動読み込みを完全に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- run_monitoring は監視用 DB として常に settings.sqlite_path（本番用パス）を使用します。テストやペーパートレードで監視を分離したい場合は注意してください。

--- 

今後の予定（短期）
- research/factor_research の完成とテスト
- 単体テスト・CI の追加（設定検証・DB 初期化・主要計算ロジックのテスト）
- 各モジュールのドキュメント強化（使用例、API 仕様）

もしリリースノートに追記してほしい詳細（例えば各関数の例、環境変数一覧、既知の回避策など）があれば教えてください。必要に応じて追記します。