CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
初期リリースとして、コードベースから推測される主要な追加機能・動作仕様をまとめています。

[0.1.0] - 2026-04-23
--------------------

Added
- 基本ランタイム・起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session を別スレッドで実行。
    - data/stop_requested.flag による外部停止監視、実行時 PID を data/execution.pid に保存する想定。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で変更可能（デフォルト 60 秒、1 未満の値は無効としてデフォルトにフォールバック）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を参照して監視データを記録する設計。
    - data/stop_requested.flag による停止監視を行い、例外を捕捉して次ポーリングへ継続する耐障害性を確保。

- 環境設定・検証ツール
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）機能を実装。
    - .env のパースは export 形式、クォート文字列、インラインコメント等に対応する堅牢な実装。
    - Settings クラスでアプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE など）。
    - 環境変数値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL、PAPER_FILL_MODE の有効値など）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - 必須・任意項目、シークレット入力、デフォルト表示、確認プロンプトを備える。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を提供。必須環境変数チェック、パスの存在チェック、YAML パースチェック（PyYAML がない場合は警告）、本番環境ガード等を実装。
    - --strict オプションで警告もエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、ファイルハンドラ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定可能な set_process_priority を実装。psutil を使用し権限不足時は警告でスキップ。
    - set_cpu_affinity でプロセスを最初の N コアに固定する機能を提供（利用可能な場合のみ実行）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順 + signal_rank によるタイブレークで選抜。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重を計算。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存ポジション比率に基づき新規候補を除外する処理（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資産乗数（1.0/0.7/0.3）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じて発注株数を計算。単元株（lot_size）丸め、per-stock cap、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページ見積）を考慮。
    - risk_based 方式では risk_pct / stop_loss_pct ベースでポジションサイズを決定。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計し検証レポートを標準出力に出力。
    - 指標: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）。
    - デフォルト閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - CLI オプションで期間指定（--from / --to）および DB パス（--db）を受け付ける。
    - SQL 実行時にテーブルが存在しない場合でも例外処理で耐性を持たせる実装。

- 研究用ファクター計算（着手）
  - research/factor_research.py（モメンタム等のファクター計算を実装する設計。DuckDB 接続を受け、prices_daily / raw_financials を参照して複数ファクターを算出する方針）
    - モメンタム関連定数とインターフェース（calc_momentum）が存在（実装は途中/継続想定）。

Changed
- パッケージメタ情報
  - kabusys.__version__ を "0.1.0" として初期設定。

Security
- （リリース時点での注意）.env は生成時に Git にコミットしない旨の注記を config_setup の出力で強調。

Notes / Configuration
- 環境変数（主なもの）
  - KABUSYS_ENV: development / paper_trading / live（必須。無効値はエラー）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: instant / partial / never / reject（paper_trading 時の模擬約定モード）
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START
- ロギング
  - 既存ハンドラを上書きして stdout と日次ファイルローテーション（logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみを使用。
- 停止制御
  - 起動スクリプトは data/stop_requested.flag（プロジェクトの data ディレクトリ配下）を監視して安全停止する設計。
- その他
  - process_priority の権限不足や未対応 OS の場合は警告を出して処理をスキップするため、非特権環境でも起動可能。

Breaking Changes
- 初期リリースのため破壊的変更はなし。

Acknowledgements / TODOs（コードから推測される今後の課題）
- research/factor_research.py の未完実装（calc_momentum の続きなど）を完成させる必要あり。
- price 欠損時のフォールバック（risk_adjustment.apply_sector_cap の TODO）や銘柄別 lot_size サポート（position_sizing の TODO）などの拡張。
- monitoring_db、SystemMonitor、ExecutionEngine、BrokerClient 等の実装詳細は別ファイル（今回の表示対象外）に依存しており、各コンポーネントの統合テスト・運用検証が必要。

参考コマンド
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

-- END --