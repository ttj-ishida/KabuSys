# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般的な方針:
- バージョニングは SemVer に従います。
- エントリは新しい順に並べます。

## [0.1.0] - 2026-04-18

Added
- 初回リリース。KabuSys の基盤機能群を追加。
  - 設定・環境変数管理
    - Settings クラスを実装（kabusys.config）。
      - 多数の設定プロパティを提供（J-Quants トークン、kabu API、LINE、DB パス、監視閾値、実行環境など）。
      - KABUSYS_ENV の検証（development / paper_trading / live）や LOG_LEVEL の検証を行う。
      - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE をサポート（入力検証あり）。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
      - .env と .env.local を読み込み、OS 環境変数を上書きから保護する仕組みを持つ。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 高機能な .env パーサを実装（kabusys.config._parse_env_line）。
      - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応。
  - 設定作成ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を初期作成・更新可能。
    - シークレット項目はマスク表示、選択肢・デフォルト提示、保存確認、ファイル書き込みをサポート。
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス・config/*.yaml の存在チェック。
    - PyYAML が利用可能な場合は YAML のパース検証を行う（未インストール時は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 起動スクリプト
    - run_execution (kabusys.run_execution)
      - 起動時にプロセス優先度を「high」に設定。
      - KABUSYS_ENV が paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止管理（PID ファイル、停止フラグ対応）。
      - RiskConfig のデフォルト値（max_position_pct など）を設定し、初期ポートフォリオ値に broker.get_available_cash() を利用。
    - run_monitoring (kabusys.run_monitoring)
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
      - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring 用 DB 初期化を実行）。
      - 停止フラグファイル検出によりループ終了、例外は log に記録して次回ポーリングに継続。
  - ロギング・プロセス管理ユーティリティ
    - logging_setup (kabusys.utils.logging_setup)
      - ルートロガーを統一的に設定。コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
      - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラのクリア処理を含む。
      - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
    - process_priority (kabusys.utils.process_priority)
      - set_process_priority(level) で Windows / POSIX を吸収して優先度設定。権限不足や未対応 OS は警告してスキップ。
      - set_cpu_affinity(cpu_count) を提供（指定なしなら変更しない）。不正な cpu_count は ValueError。
  - ポートフォリオ構築ライブラリ（kabusys.portfolio）
    - portfolio_builder
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（同点は signal_rank でブレーク）。
      - calc_equal_weights / calc_score_weights: 重み計算。スコア合計が 0 の場合は等分配へフォールバック（警告ログ）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限チェック。既存保有のセクター時価を計算して上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返し、未知レジームは警告の上 1.0 にフォールバック。
    - position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数決定ロジック。
      - lot_size（単元）単位で丸め、max_position_pct / max_utilization / cost_buffer（スリッページ等）を考慮した aggregate cap スケーリング、余りの再配分アルゴリズムを実装。
  - 研究用モジュール（kabusys.research）
    - factor_research（モジュール設計とモメンタム計算の骨格を追加）
      - DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等のファクターを計算する設計（P95 などの計算ユーティリティを含む）。
  - ツール
    - paper_verification_report (kabusys.tools.paper_verification_report)
      - Paper Trading 用 SQLite から検証レポートを生成。稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL 判定を行う。
      - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
      - 標準的な閾値（稼働率 99%、成功率 90% など）を定義して判定する。
  - パッケージ初期化
    - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Security
- なし。

Notes / 内部メモ
- run_execution / run_monitoring はプロセス優先度を最初に設定する設計（重要処理の優先度確保）。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後の挙動に注意。自動読み込みを無効化するフラグを用意。
- 一部モジュール（例: factor_research）は設計・骨格実装の段階であり、データ不足時のフォールバックや追加検証が必要になる可能性がある。

--- 

過去のリリース履歴はここに追加していきます。問題点・改善要望・バグ報告は Issue を作成してください。