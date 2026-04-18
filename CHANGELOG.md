Keep a Changelog
=================

すべての重要な変更点をこのファイルに記載します。  
このプロジェクトでは「Keep a Changelog」の慣例に従っています。

0.1.0 - 2026-04-18
-----------------

Added
- 初期リリース: KabuSys ベースライン機能を追加。
  - 実行 (Execution)
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV に応じて paper_trading 環境では MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（data/paper_trading.db）を利用して本番 DB と分離。
      - BrokerClientFactory によりブローカークライアントを抽象化。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせた実行フローを構築。
      - ExecutionEngine はデーモンスレッドで run_session を実行し、data/execution.pid に PID を記録、停止フラグ (data/stop_requested.flag) による安全停止をサポート。
      - RiskManager のデフォルト設定 (max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等) を導入。
  - 監視 (Monitoring)
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は init_monitoring_db でテーブルを初期化し、SQLite（settings.sqlite_path）および DuckDB を使用。
      - 停止フラグ (data/stop_requested.flag) によるループ停止をサポート。
  - 設定管理
    - config.py: Settings クラスを実装。
      - .env 自動読み込み機能 (.env / .env.local) を提供（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - .env パーシングは export 形式、クォート文字列、インラインコメント（スペースで区切られた #）等に対応。
      - 各種設定プロパティ（J-Quants / kabu API / DuckDB / SQLite / paper_trading / 監視閾値 / PID/Kill flag 等）を提供し、入力検証を行う（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
      - 入力補助、シークレットのマスク表示、既存 .env の読み込み・再利用をサポート。
    - validate_config.py: 起動前設定検証 CLI を追加。
      - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境の追加ガードなどを実行。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: シグナルをスコア降順にソートし上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供（スコア合計が 0 の場合は等配分にフォールバックし警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（売却予定銘柄の除外対応、"unknown" セクターは上限適用除外）。
      - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 にフォールバックして警告を出力。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数算出ロジックを実装。
      - 単元株 (lot_size) 丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積り）反映、残余キャッシュに基づく再配分ロジックを搭載。
  - ユーティリティ
    - utils/logging_setup.py
      - 共通ログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。
      - LOG_DIR 作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - psutil を利用したプロセス優先度設定の抽象化（Windows / POSIX の差分吸収）。
      - set_cpu_affinity による CPU ピン留め機能を提供。権限不足や未対応環境時は警告を出力してスキップ。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI を追加。日付レンジ指定（--from/--to）および DB 指定（--db）に対応。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等の指標を算出し、定められた閾値と比較して PASS/FAIL を判定。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- init_monitoring_db 呼び出しを冪等にして監視テーブルの存在を保証（起動スクリプト内で必須テーブルの初期化を明示）。
- ログ設定: stdout を標準出力に使うことで cron/Task Scheduler 等とのリダイレクト運用を想定。

Documentation / Notes
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト等で利用）。
- run_monitoring は監視用 DB 接続に環境に依らず settings.sqlite_path（本番監視 DB）を使用する仕様。
- run_execution は paper_trading 時に settings.paper_sqlite_path を使用して本番 DB と完全分離する仕様。
- paper_verification_report はデフォルトで PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照する。
- 複数箇所にて「価格が取得できない（0.0/None）場合のフォールバック」が TODO として残っている（position_sizing / risk_adjustment）。現状では価格欠損により過小評価される可能性があるため注意が必要。

Known issues / Limitations
- research/factor_research.py において calc_momentum の実装が途中（ファイル末尾が途切れている）。ファクター計算モジュールは設計方針・定数群は定義されているが、一部実装が未完了。
- 一部の機能（例: 銘柄別 lot_size の柔軟化、価格フォールバックロジック、より細かいログローテーション設定など）は将来の改善項目として TODO コメントが存在する。
- psutil による優先度設定や CPU affinity は権限・プラットフォーム依存で失敗する可能性があり、その場合は警告を出してスキップする設計。

開発者向け補足
- ソース内で使用される各種ファイルパス（logs/, data/, config/）はデフォルトを持つが、環境変数で上書き可能。
- config/*.yaml の存在確認とパース検証は PyYAML の有無に依存。PyYAML 未導入時は YAML 内容検証をスキップして警告を出す。
- ログの既存ハンドラは setup_logging の呼出時に flush/close のうえ削除するため、複数回の初期化による二重出力を防止する。

Acknowledgments
- 初期設計は PortfolioConstruction.md / StrategyModel.md 等の設計文書に基づいており、各モジュールは設計書のセクション対応（コメント）を参照できるように実装されています。