# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-04-25

### Added
- パッケージ初期リリース。
- 設定管理
  - Settings クラス（kabusys.config）を追加。環境変数／.env ファイルから各種設定を取得する抽象化を提供。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - 環境変数パースの強化:
    - export プレフィクス対応
    - シングル/ダブルクォートとバックスラッシュエスケープの正しい処理
    - インラインコメントの取り扱い
  - Settings により、DUCKDB/SQLite パス、KABUSYS_ENV（development/paper_trading/live）、ログレベル、paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）等をプロパティで提供。
- 環境設定ウィザード
  - config_setup CLI（kabusys.config_setup）を追加。対話式で .env を初期作成／更新可能。既存値の利用、シークレットマスク表示、保存前確認などを実装。
- 設定検証ツール
  - validate_config CLI（kabusys.validate_config）を追加。必須環境変数やパス、config/*.yaml の存在・パース検証、KABUSYS_ENV による本番ガード等をチェック。--strict オプションで警告を FAIL 扱いにできる。
- 実行スクリプト
  - run_execution（kabusys.run_execution）を追加。ExecutionEngine の起動フローを実装:
    - プロセス優先度を高に設定
    - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む）
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て
    - ExecutionEngine をデーモンスレッドで実行、停止フラグ（data/stop_requested.flag）検知で安全に停止
    - PID ファイル管理（data/execution.pid）
  - run_monitoring（kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず production の sqlite_path を使用して監視データを記録
    - 停止フラグ検知、例外処理、リソースクローズを実装
- モニタリング DB 初期化フック（init_monitoring_db）を利用して監視テーブルの存在を保証（冪等）。
- ツール
  - paper_verification_report（kabusys.tools.paper_verification_report）を追加。Paper Trading 用 SQLite から以下を集計して検証レポートを生成:
    - システム稼働率（uptime）
    - 注文成功率 / 送信率
    - リスク却下数
    - API レイテンシ（平均 / 最大 / P95）
    - デフォルトの合格基準（稼働率 >= 99%、成立率 >= 90% など）を定義し PASS/FAIL 判定
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア順で候補選定（タイブレーク用 signal_rank）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア重み配分（全銘柄スコアが 0 の場合は等額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有からセクター比率を算出し、上限超過セクターの新規候補を除外）
    - calc_regime_multiplier: 市場レジーム別投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に従った発注株数決定、単元株（lot_size）で丸め、aggregate cap によるスケーリングと残差配分ロジックを実装
- ユーティリティ
  - logging_setup（kabusys.utils.logging_setup）:
    - setup_logging: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラを一旦クリア。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみにフォールバック。
  - process_priority（kabusys.utils.process_priority）:
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定。権限不足時は警告でスキップ。
    - set_cpu_affinity: プロセスの CPU affinity を固定（コア数指定）。権限不足時は警告でスキップ。
- リサーチ
  - research/factor_research: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。calc_momentum 等の関数が追加されており、DuckDB の prices_daily テーブルを参照してファクター計算を行う設計。

### Changed
- データベース取り扱い
  - paper_trading 環境では SQLite を完全に分離（Settings.paper_sqlite_path を導入）。これにより paper_trading と本番監視 DB の混同を防止。
- ログ出力
  - setup_logging により stdout を標準のログストリームに使用（cron / scheduler とリダイレクトしやすくするため stderr ではなく stdout を採用）。
- Monitoring 動作
  - MONITOR_POLL_INTERVAL の環境変数値検証を追加。0 以下や非数値は警告を出してデフォルトにフォールバック。

### Fixed
- 環境変数パースの不整合への対処:
  - .env の quoted value 内でのバックスラッシュエスケープ処理やインラインコメントの誤解釈を修正。
- ログハンドラの二重追加を防止（既存ハンドラをクリアしてから再設定）。

### Notes
- factor_research モジュールは主要な設計と関数の骨組み（calc_momentum 等）を追加していますが、一部実装が継続中の可能性があります（ソースが途中で切れている部分があります）。実運用前に該当モジュールの完全実装とテストを推奨します。
- ExecutionEngine / Broker 等の実装本体（kabusys.execution.*）は本変更履歴に含まれますが、ブローカーごとの具体的な接続実装や外部 API 依存部分は別途検証が必要です。
- Paper Trading の挙動は PAPER_FILL_MODE により制御されます（instant/partial/never/reject）。無効な値は Settings で ValueError を送出します。

### Deprecated
- なし

### Removed
- なし

---

今後の変更は Unreleased セクションで管理してください。