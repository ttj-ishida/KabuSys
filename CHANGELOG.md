# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定版リリースや主要な追加・変更点を日本語でまとめています。

全般的な注意
- リポジトリのバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" に設定されています。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション構成を追加
  - パッケージ初期リリースとして、監視・実行・ポートフォリオ構築・ユーティリティ類・CLIツールなどの主要モジュールを実装。
- 実行エントリスクリプト
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が paper_trading の場合は専用の Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行および停止フラグ（data/stop_requested.flag）による安全停止機構を実装。
    - 実行時の PID 格納ファイルパスを管理（data/execution.pid）。
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスも起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の動作（安全設計）。
- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - 環境変数・設定管理を集中化。多くの getter を通じて設定値を取得する（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK 閾値など）。
    - PAPER_FILL_MODE（paper_trading 用の fill モード）を検証して許容値のみ受け入れる（"instant", "partial", "never", "reject"）。
    - KABUSYS_ENV の有効値検証（development, paper_trading, live）。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）を提供。OS 環境変数を優先し、.env.local を .env 上書き可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - settings = Settings() の単一インスタンスをエクスポート。
  - .env パーサ
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無しでの条件付き扱い）などを正しく扱うパーサを実装。
- 設定支援 CLI
  - config_setup (src/kabusys/config_setup.py)
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値、選択肢、シークレット入力、生成テンプレートファイルの書き出し機能を提供。
    - 生成される .env テンプレートには警告コメント（絶対に Git にコミットしない等）を含む。
  - validate_config (src/kabusys/validate_config.py)
    - .env や config/*.yaml の基本的な健全性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML の有無によるスキップあり）、本番環境向けの追加警告等を出力。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギングユーティリティ
  - setup_logging (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定する共通設定を実装。
    - ログレベル/ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
- プロセス優先度 / CPU affinity
  - process_priority (src/kabusys/utils/process_priority.py)
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を実装（Windows/Linux/macOS 対応、psutil 使用、失敗時は警告）。
    - set_cpu_affinity 関数を追加し、最初の N コアへ固定する機能を提供。
- ポートフォリオ構築ライブラリ
  - portfolio モジュール (src/kabusys/portfolio/*)
    - portfolio_builder
      - select_candidates: BUY シグナルのスコア降順フィルタリング（タイブレークに signal_rank を使用）。
      - calc_equal_weights, calc_score_weights: 等重 / スコア加重の重み計算。score 全てが 0 の場合は等重にフォールバックして警告を出す。
    - risk_adjustment
      - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1セクター上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは無視）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3。未知は 1.0 でフォールバックし警告）。
    - position_sizing
      - calc_position_sizes: 複数の配分方式（"risk_based", "equal", "score"）に対応する株数決定ロジックを実装。単元株（lot_size）で丸め、per-stock 上限、aggregate cap（available_cash）でスケールダウンする機構、コストバッファを考慮した保守的な見積もり、残余配分のための端数処理（fractional remainders）を含む。
    - portfolio パッケージのエクスポートは次の関数群を提供:
      - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- Paper Trading 検証ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード結果を SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を出力する CLI を実装。
    - CLI オプション --from / --to（日付範囲）および --db（DB パス）をサポート。
    - デフォルト基準値を定義（稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）。
- 研究用ファクター計算（着手）
  - research/factor_research.py にてモメンタム等のファクター計算関数群の設計・実装を追加。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照して計算する方針（モジュールは途中まで実装）。

### Changed
- なし（初期リリースのため、既存コードからの変更履歴はなし）。

### Fixed
- なし（初期リリース）。

### Security
- なし（特別なセキュリティ修正はなし）。

---

備考（実装上の重要な挙動）
- run_monitoring は MONITOR_POLL_INTERVAL を整数として読み取り、1 未満や不正値の場合はデフォルト 60 秒にフォールバックして警告を出力します。
- Settings は .env 自動ロード時、OS 環境変数を保護（上書き不可）します。テスト等で自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- run_execution は paper_trading 環境時に paper_sqlite_path を用いることで本番 DB と完全分離する設計です。
- logging_setup は stdout を StreamHandler に使用するため、Task Scheduler / cron 等で stdout/stderr を一本化している運用に配慮しています。
- process_priority の適用は psutil の権限や OS に依存するため失敗時は警告でフォールバックします。

この CHANGELOG は、コードベースから推測できる機能・設計方針に基づいて作成しています。実際のリリースノートや運用手順には、デプロイ手順や外部依存（psutil, duckdb, PyYAML など）のバージョン・インストール要件を併記することを推奨します。