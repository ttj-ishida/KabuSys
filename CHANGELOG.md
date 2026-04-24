# Changelog

すべての注目すべき変更をここに記述します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-24

### Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」の基本機能を実装。
- 起動スクリプト / デーモン風ループ
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - Engine を別スレッドで実行し、data/stop_requested.flag による外部停止検知を実装。実行中の PID を data/execution.pid に書き込む仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず本番用 sqlite_path を使用する旨を明示。
    - 外部停止フラグ（data/stop_requested.flag）検知および KeyboardInterrupt のハンドリング。
- 設定管理
  - config.py
    - .env 自動ロード（プロジェクトルートの判定: .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順序（OS 環境変数を保護して上書き制御）。
    - 詳細な .env パーサを実装（export プレフィックス、クォート値、エスケープやインラインコメント処理に対応）。
    - Settings クラスで環境変数の取得を型付きプロパティで提供（DB パス、PID/kill flag パス、しきい値、PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE（instant/partial/never/reject）サポート。
    - is_live / is_paper / is_dev の判定ユーティリティ。
- 設定支援・検証ツール
  - config_setup.py
    - 対話式の .env 作成ウィザード（既存 .env の読み込み、マスク表示、確認後ファイル書き込み）。
    - デフォルト値や選択肢を提示（KABUSYS_ENV、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
  - validate_config.py
    - 起動前検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML を用いたパース検証（PyYAML 未インストール時はスキップ））。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - stdout へ StreamHandler を出力（cron/task 環境でのリダイレクトを想定）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）を追加。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみ継続。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py
    - psutil 経由でクロスプラットフォームにプロセス優先度設定（high/normal/low）を実装。Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収。
    - カレントプロセスの CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時に安全にスキップして警告出力。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。全スコアが 0 の場合は等分配へフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターはチェック対象外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）に丸め、ポジション上限・投下資金上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを使った再配分アルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading SQLite（デフォルト: data/paper_trading.db）を対象に検証レポートを生成する CLI。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均、最大、P95）を集計。
    - 日付フィルタ (--from/--to) に対応。閾値に基づく PASS/FAIL 判定と詳細出力を行う。
- DuckDB 統合
  - run_* スクリプトや一部モジュールで分析用 DuckDB（デフォルト: data/kabusys.duckdb）への接続を使用。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため履歴上の変更なし）

### Fixed
- （初回リリースのため履歴上の修正なし）

### Notes / 設定上の重要事項
- .env 自動読み込み
  - デフォルトではプロジェクトルートを検出して .env/.env.local を自動的に読み込みます。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされません。
- MONITOR_POLL_INTERVAL
  - run_monitoring.py のポーリング間隔を秒単位で環境変数 MONITOR_POLL_INTERVAL により上書き可能。不正な値（0 以下や整数変換不能）はデフォルト 60 秒にフォールバック。
- Paper Trading と本番 DB の分離
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）で指定した別 DB を使用し、本番の monitoring DB と完全に分離されます。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動（instant/partial/never/reject）を制御できます。
- ロギング
  - setup_logging は stdout を主要なコンソール出力先として使用します（stderr ではない）。
  - ログ出力先ディレクトリの作成に失敗した場合はファイル出力を無効化し、コンソールのみで継続します。
- 実行優先度
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出してプロセス優先度を上げようとします。権限がない場合は警告を出してスキップされます。
- validate_config の注意点
  - PyYAML がインストールされていない場合、config/*.yaml の内容検証はスキップされ、警告が出ます。
  - --strict を付けると警告がある場合に exit(1) で終了します（CI 等での事前チェック向け）。
- 外部停止フラグ
  - run_execution/run_monitoring はプロジェクト直下の data/stop_requested.flag を監視し、ファイルが存在すると安全に停止する動作を備えています。

### Known limitations / TODO
- research/factor_research.py はファクター計算の主要ロジック（Momentum / Value / Volatility / Liquidity）を意図しており、DuckDB の prices_daily/raw_financials を参照して計算します。リポジトリ内の実装は進行中の箇所がある可能性があります（momentum 等の関数を含む）。
- position_sizing の lot_size は現状全銘柄共通固定。将来的に銘柄別 lot_map を受け取る拡張を想定。
- apply_sector_cap の価格欠損時の扱い（price が欠損するとエクスポージャーが過少評価される）に関する改善メモを残しています（前日終値や原価でのフォールバック等を検討）。

### Security
- （このリリースでの既知のセキュリティ脆弱性はありません）

---

リリースに関する質問や、追加で CHANGELOG に盛り込みたい差分（例えば細かいコミット単位の追記）があればお知らせください。