CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし（初回リリース以降の変更はここに記載します）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアユーティリティとコンポーネント群を追加。
  - 実行/監視スクリプト
    - run_execution.py
      - ExecutionEngine 起動用スクリプトを提供。KABUSYS_ENV が paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する設計。
      - BrokerClientFactory を利用してブローカークライアントを構築、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全停止。
      - PID ファイル出力（data/execution.pid）や停止フラグ検出ロジックを含む。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に関わらず本番 sqlite_path を使用。
      - 実行中の例外はログ出力して次のポーリングまで待機する堅牢なループ実装。停止フラグの検出で安全に終了。
  - 設定管理
    - config.py
      - .env の自動読み込み機構（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - .env のパースは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメント等に対応する堅牢実装。
      - Settings クラスで環境変数をプロパティとしてラップ。多数の設定プロパティ（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル等）を提供。入力値のバリデーションを実施（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
    - config_setup.py
      - 対話式 .env ウィザードを提供。既存 .env の読み込み・編集、デフォルト値・選択肢の提示、シークレット扱いのマスク表示、保存操作をサポート。
  - 設定検証ツール
    - validate_config.py
      - 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスや config/*.yaml ファイルの存在・パース（PyYAML が利用可能な場合）を検証。
      - --strict オプションで警告を失敗扱いにできる。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみ継続する安全設計。
    - utils/process_priority.py
      - psutil を使ったクロスプラットフォームのプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 設定。Windows / POSIX（Linux/Mac/FreeBSD）向けに差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py
      - シグナル選択（スコア降順・タイブレークロジック）と重み計算（等金額・スコア加重）。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）。既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外。unknown セクターは上限の対象外。
      - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームは警告の上フォールバック 1.0）。
    - portfolio/position_sizing.py
      - position sizing の純粋関数群。allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケールダウン）を実装。cost_buffer による保守的見積りと残余の再配分アルゴリズムを備える。
    - portfolio/__init__.py で主要 API をエクスポート。
  - リサーチ（部分追加）
    - research/factor_research.py
      - DuckDB を用いたファクター計算モジュールの骨子（モメンタム / MA200 / ATR 等）を実装開始。設計方針と定数が整備され、一部関数（calc_momentum など）の実装が含まれる（ファイル末尾は省略）。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - Paper Trading の SQLite を参照して検証レポートを生成する CLI。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計。デフォルト閾値を定義し PASS/FAIL 判定を行う。
      - DB パスはコマンドライン --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。P95 は独自実装で算出。
  - パッケージ基礎
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- N/A（初回リリースのため過去バージョンからの変更は無し）

Fixed
- N/A（初回リリース）

Security
- 環境変数読み込み時に OS の既存環境変数を保護する仕組みを導入（.env 自動ロード時に OS 環境変数を上書きしない）。config._load_env_file の protected 引数で実装。

Notes / 運用上のポイント
- .env 自動読み込み
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします。テストやパッケージ化環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- Paper Trading と本番 DB の分離
  - run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番の monitoring.db とデータ分離します。
- 監視（monitoring）
  - run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を制御可能（整数秒、1 秒以上）。不正値はログ警告を出してデフォルト 60 秒にフォールバックします。
  - 監視 DB 初期化（init_monitoring_db）を起動時に実行し、必要テーブルの存在を保証します（冪等）。
- 停止制御
  - data/stop_requested.flag（プロジェクトルート配下）や設定された kill/stop フラグパスで停止を検知し、安全に終了・停止する設計です。KILL_FLAG_CLEAR_ON_START 設定は本番での自動クリアに注意（validate_config が警告）。
- ログ
  - デフォルトは stdout と logs/<app>.log（日次ローテート、30 日保持）。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみ継続します。
- プロセス優先度・CPU アフィニティ
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します。権限や OS により設定が行えない場合は警告を出してスキップします。

Breaking Changes
- なし（初回リリース）

References / Usage Examples
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Contributing
- 変更履歴はこのファイルに追記してください。新機能追加や修正はセマンティックバージョニングに従ってバージョンを更新してください。