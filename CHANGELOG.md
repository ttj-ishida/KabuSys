KEEP A CHANGELOG
全ての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

以下は、提示されたコードベースの内容から推測して作成した変更履歴です。実装意図や挙動はコード内コメント／実装に基づいています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25
初回リリース（推測）。日本株自動売買システム KabuSys の基本機能群を実装。

### Added
- 基本パッケージ初期化
  - kabusys パッケージのバージョン定義: __version__ = "0.1.0"。
- 環境設定・読み込み
  - .env 自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序をサポート。OS 環境変数を保護するための上書き振る舞いを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。
  - .env パーサー実装: export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを追加し、環境変数の取得・バリデーションをプロパティとして提供（J-Quants / kabu API / DB パス / ログ設定 / 監視設定等）。
  - PAPER_FILL_MODE 等の列挙値チェックを実装（無効値は ValueError）。
  - is_live / is_paper / is_dev などの環境判定プロパティを提供。
- 起動用ユーティリティ・CLI
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢、デフォルト値サポートを実装。
    - .env 書き込みテンプレートを提供（Git にコミットしない旨のヘッダを含む）。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス／ディレクトリの存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング設定ユーティリティ
  - setup_logging を追加。
    - stdout 出力の StreamHandler（stdout を使用）と、日次ローテート + 30日保持の TimedRotatingFileHandler をルートロガーへ追加。
    - 既存ハンドラのクリア機能、ログディレクトリ解決（LOG_DIR / 引数 / デフォルト）および作成失敗時のフォールバックを実装。
- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level) / set_cpu_affinity(count) を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収。psutil を用いて nice / priority / cpu_affinity を設定。
    - 権限不足や未実装プラットフォームは警告でフォールバック。
- 実行系 & 監視スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory を通じて環境に応じたブローカクライアント（実ブローカー / Mock）を選択。
    - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - 停止フラグファイル（data/stop_requested.flag）の監視、PID ファイル出力（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプトを追加。
    - 環境に関わらず監視用 DB（monitoring.db）を本番パスで使用する仕様（監視は本番 DB 記録を想定）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視停止用フラグ（data/stop_requested.flag）の検知と安全終了、check_once() の例外をキャッチしてループ継続。
- モジュール: portfolio（銘柄選定・配分・ポジションサイジング・リスク調整）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア合計が 0 の場合は等金額にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限超過セクターの候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知はフォールバック 1.0 と警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）の丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的見積もり、残差処理による lot 単位での追加割当てアルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計してレポート出力。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, P95 レイテンシ（ms）, リスク却下数 等。
    - デフォルト閾値（稼働率 99% 等）を定義し、PASS/FAIL 判定を出力。
    - --from/--to/--db オプションによる期間/DB 指定をサポート。
- research/factor_research（未完の箇所あり）
  - Momentum 等のファクター計算骨子を実装（DuckDB 接続を受け prices_daily / raw_financials を利用する想定）。
  - 設計上、純粋関数で DB 以外に副作用を持たないことを想定。

### Changed
- ロギング
  - stdout を StreamHandler に使うことで cron/task などでの stdout/stderr 集約に対応。
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソール出力のみで継続するロバスト化を実施。
- DB 周りの取り扱い
  - run_execution は paper_trading 時に専用 SQLite を使用して本番 DB と分離（安全設計）。
  - init_monitoring_db 呼び出しを行い、監視テーブルの存在を冪等に保証。
- プロセス管理
  - 起動直後にプロセス優先度を High に設定する呼び出しを各起動スクリプトで行う（set_process_priority("high")）。
  - ExecutionEngine はデーモンスレッドで run_session を起動し、メインスレッドで停止フラグを監視して安全停止を行う実装に。

### Fixed / Robustness
- 各種リソースクローズを finally で保証（SQLite / DuckDB 接続の close）。
- run_monitoring のポーリング間隔読み取りで 0 以下や非整数が与えられた場合に ValueError を避け、警告してデフォルトにフォールバック。
- monitor.check_once() の例外はキャッチしてログ出力し、次回ポーリングへ影響を与えないように（フォールトトレランス）。
- config_setup の対話入力で中断（EOF/KeyboardInterrupt）をハンドルし、未保存時に適切に終了。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし、警告を出す。

### Security / Documentation
- .env ファイルに関する注意を config_setup 上で強調（.env を Git にコミットしない旨のヘッダを追加）。
- validate_config による設定検証で本番環境（KABUSYS_ENV=live）時のガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定）チェックを追加。

### Known limitations / Notes
- research/factor_research の実装はファイル末尾で途切れており、細部実装（SQL クエリなど）は未完の箇所があるように見える（追加実装が必要）。
- position_sizing の price フォールバック処理（価格欠損時の代替値使用）は TODO コメントが残っており、将来的な改善余地あり。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで動作しない可能性があり、その場合は警告でスキップする設計。
- run_monitoring は監視 DB を「環境にかかわらず本番 sqlite_path を使用」する設計であり、監視データの取り扱いポリシーに注意が必要。

---

注: 上記は提示されたソースコードからの推測に基づく CHANGELOG です。実際のリリースノート作成ではコミット履歴やリリース担当者の記録を参照して確定してください。必要であれば、この CHANGELOG を英語版に変換したり、項目をより詳細化（各関数の例や CLI 使い方の抜粋）することもできます。