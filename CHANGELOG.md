# CHANGELOG

すべての注目すべき変更を日付順に記載します。  
フォーマットは「Keep a Changelog」準拠です。

次の規約を使用しています:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当する場合に記載

## [0.1.0] - 2026-04-21
初回リリース — KabuSys 基本コンポーネントを実装。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - 共通設定管理モジュール (kabusys.config) を実装。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサの実装（export プレフィックス、クォート文字列、インラインコメント、エスケープ処理に対応）。
    - Settings クラスに各種設定プロパティを実装（DB パス、ログレベル、KABUSYS_ENV 判定、Paper Trading 設定等）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。

- 実行系 / 監視
  - 実行エンジン起動スクリプト run_execution を追加。
    - KABUSYS_ENV=paper_trading の場合に専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するワークフローを実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理、スレッドでの実行。
    - RiskManager 用の初期デフォルト設定を提供（max_position_pct 等）。
  - 監視起動スクリプト run_monitoring を追加。
    - SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ検出によるループ終了処理と例外ハンドリング。

- 監査・検証
  - 設定検証 CLI (kabusys.validate_config) を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML がある場合の）パース検証、KABUSYS_ENV=live 向けの追加ガードチェック。
    - --strict フラグで警告も失敗扱いにできる。
  - 環境設定ウィザード CLI (kabusys.config_setup) を追加。
    - 対話式で .env の初期生成・更新をサポート。シークレット値はマスク表示、デフォルト/既存値の再利用、保存確認、テンプレート書き出しを実装。

- ロギング・プロセス管理ユーティリティ
  - logging_setup を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_LEVEL, LOG_DIR の環境変数または引数で設定可能。既存ハンドラのクリア処理を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
  - process_priority を追加。
    - Windows と POSIX の差を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - psutil のアクセス例外を捕捉して安全にフォールバック。

- ポートフォリオ構築（pure functions）
  - portfolio モジュールを追加（DB 非依存、メモリ計算のみ）。
  - portfolio.portfolio_builder:
    - select_candidates：BUY シグナルをスコア降順で選択。
    - calc_equal_weights：等金額配分。
    - calc_score_weights：スコア加重配分（全スコア 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap：セクター集中上限（max_sector_pct）を適用して候補をフィルタ。unknown セクターは上限適用除外。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は警告して 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes：allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を決定。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、端数配分アルゴリズム等を実装。
    - prices 未取得時のスキップやログ出力を考慮。

- ツール
  - tools/paper_verification_report を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を参照して検証レポートを生成。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg / max / P95）を集計。
    - P95 計算ユーティリティ、期間フィルタ（--from、--to）、DB パスの CLI/環境変数指定対応。
    - デフォルト閾値を定義して PASS/FAIL 判定を出力（稼働率 >= 99%、成立率 >= 90% 等）。

- 研究用（研究/実験的）
  - research/factor_research の基礎実装（ファクター計算の設計方針と定数、calc_momentum の雛形）。DuckDB を用いた prices_daily / raw_financials の参照を想定。

### Changed
- 設計上の分離
  - 実行エンジンと監視で使用する SQLite DB の取り扱いを明確化（paper_trading は専用 DB を使用、監視は環境にかかわらず本番 sqlite_path を使用する）により本番とペーパートレードのデータ分離を徹底。

### Fixed
- 環境変数パーサの堅牢化
  - .env パーサがクォート文字列内のバックスラッシュエスケープやインラインコメントに対応するように改善（誤ったトークン分割の回避）。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値対策
  - 0 以下や非数が設定された場合に ValueError を起こさないようにデフォルトへフォールバックし、警告ログを出力。

### Notes / Implementation details
- run_execution と run_monitoring は停止フラグ（data/stop_requested.flag）を用いた外部制御に対応。PID ファイル管理やデータベース接続のクリーンアップを行う。
- logging_setup は標準出力を stdout に向ける（cron やタスクスケジューラでのログ取り扱いを想定）。
- process_priority, set_cpu_affinity は権限不足や未実装 API に対しては警告を出して処理を継続する（安全第一）。
- config_validate は PyYAML の有無を考慮して YAML パースの可否を切り替える（依存がない環境でも実行可能）。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

（注）上記はリポジトリ内のソースコードを基に推測して作成した変更履歴です。実際のリリースノートや履歴管理が別途存在する場合はそちらを優先してください。