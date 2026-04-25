# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。重要な変更点・追加機能をコードベースから推測して日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-25
初回リリース。本バージョンは自動売買システム KabuSys のコア機能群（実行・監視ランチャー、設定管理、ポートフォリオ構築、ユーティリティ、検証ツールなど）を含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。BrokerClientFactory を用いて実ブローカーまたは MockBrokerClient（KABUSYS_ENV=paper_trading）を生成する。
    - paper_trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止、スレッドでのエンジン実行を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、初期ポートフォリオ値をブローカー残高から取得して設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動（運用上の設計）を採用。
    - 停止フラグ検出によるループ終了、例外のログ捕捉と継続運用を実装。

- 設定管理
  - config.py
    - .env 自動読み込み機能を提供（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順・上書きルールを実装（OS 環境変数は保護）。
    - .env のパースはシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等を考慮した堅牢な実装。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、DB パス、paper_fill_mode 等）をプロパティ経由で取得。入力値のバリデーション（env 値チェック、paper_fill_mode の有効値チェックなど）を実装。
    - Settings インスタンス（settings）をデフォルトでエクスポート。

  - config_setup.py
    - 対話式ウィザードを実装し .env の初期作成・更新を支援。既存 .env の読み込み、シークレット項目のマスク、保存テンプレートの生成を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備をチェックする CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML がある場合）などを実装。
    - --strict オプションで警告を失敗（exit 1）として扱える。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算して上限超過セクターの候補除外を行う。unknown セクターは上限適用外とする挙動。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告を出し 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）やコストバッファ考慮の再配分ロジックを実装。
    - price 欠損時のスキップやログ出力など安全側の実装を含む。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間（--from/--to）で system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（Avg/Max/P95）を集計し PASS/FAIL 判定を出力。閾値はコード内定義で調整可能。
  - research/factor_research.py（初期実装）
    - ファクター計算モジュールの骨格（モメンタム等を計算する方針と定数）を追加。DuckDB を用いた prices_daily 参照設計。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップ関数 setup_logging を追加。標準出力（stdout）用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。既存ハンドラのクリア、ログレベル/ログディレクトリの解決ルール、ファイル作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）向けプロセス優先度設定 set_process_priority と CPU affinity 設定 set_cpu_affinity を実装。psutil を利用し、権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

- パッケージ化
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で宣言。

### Changed
- （初回リリースのため該当なし）  

### Fixed
- （初回リリースのため該当なし）

### Notes / 運用上の注意
- 環境変数自動読み込み
  - デフォルトでプロジェクトルートが検出されれば .env を自動読み込みします。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み順: OS環境変数 > .env.local > .env（.env.local は .env の上書きに使用）。
- DB 関連
  - 監視（run_monitoring）は sqlite_path（デフォルト data/monitoring.db）を本番用として常に使用する設計です。Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と分離されます。
  - DuckDB（デフォルト data/kabusys.duckdb）は分析用に使われます。
- 停止制御
  - data/stop_requested.flag（またはプロジェクトルートの data ディレクトリ内の同名ファイル）を置くことで実行中プロセスに安全停止を促す仕組みを採用しています。
  - 実運用では Kill Switch（KILL_FLAG_PATH など）や PID ファイル（PID_FILE_PATH）を適切に管理してください。
- ログ
  - デフォルトは logs/ ディレクトリ。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続します。
- プロセス優先度
  - set_process_priority("high") を起動時に呼び出しています。権限不足や OS 非対応時は警告が出て処理は継続しますが、意図した優先度にならない可能性があります。
- Paper Trading
  - PAPER_FILL_MODE（instant/partial/never/reject）をサポートし、不正値は ValueError を発生させます。
- validate_config により起動前に設定検証を行うことを強く推奨します（--strict で警告も失敗扱いにできます）。

ご要望があれば、この CHANGELOG をプロジェクトの既存バージョンに合わせて調整したり、項目を追加・細分化してさらに詳細な変更履歴（ファイル単位やコミット参照付き）に整形できます。どの形式で出力したいか（ファイルに書き出し、Git タグとの紐付け等）を指定してください。