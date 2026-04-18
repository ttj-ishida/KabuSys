# CHANGELOG

すべての変更点は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 初回リリース: KabuSys 基本モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動用スクリプトを追加。
  - run_execution: ExecutionEngine を起動するエントリポイント。プロセス起動時にプロセス優先度を "high" に設定し、別スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）検出時に安全に停止する。
  - run_monitoring: SystemMonitor のポーリングループを開始するエントリポイント。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。監視プロセスは環境に関係なく本番の sqlite_path を使用して監視 DB を初期化する。
- 設定・環境変数管理を追加。
  - config.Settings クラス: 各種環境変数の取得とバリデーションを提供（J-Quants、kabuAPI、DBパス、各種閾値、実行環境判定など）。
  - 自動 .env 読み込み機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` → `.env.local` の順に読み込み。OS 環境変数は保護（上書き防止）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを抑止可能。
  - .env パースの細かい挙動を実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント取り扱いルール）。
  - 設定ウィザード CLI（config_setup）を追加。対話式で .env を作成・更新する機能を提供（シークレット項目のマスク表示、デフォルト値、保存確認付き）。
  - 設定検証 CLI（validate_config）を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML 未導入時は警告）および本番環境時の追加ガード（LINE 通知設定、Kill Flag の自動クリア設定の警告）を実装。`--strict` で警告を失敗扱いにできる。
- ログ/プロセス関連ユーティリティを追加。
  - utils.logging_setup.setup_logging: ルートロガーに StreamHandler（stdout）と日次ローテートする TimedRotatingFileHandler を設定。ログディレクトリの自動作成、既存ハンドラのクリア、環境変数/引数によるログレベルとログディレクトリ解決をサポート。
  - utils.process_priority: Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初 N コアに固定するユーティリティも提供。権限不足などで失敗した場合は警告を出してスキップする。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内計算）。
  - portfolio.portfolio_builder:
    - select_candidates: シグナルをスコア降順でソートして上位 N 件を返す（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等配分にフォールバックして WARNING）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別時価を計算し、セクターの保有比率が上限を超える場合は同セクターの新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバックし警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を決定。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash に合わせてスケーリング）、cost_buffer（手数料・スリッページの保守的見積り）対応。スケーリング時には端数処理ロジックにより残余キャッシュで lot 単位の追加配分を行う。
- Execution 周りの基本コンポーネントを追加（実装ファイルは参照箇所あり）。
  - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading では MockBrokerClient を使い、paper_trading 専用 SQLite DB に記録して本番 DB と分離）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てロジック（実行時に RiskConfig のデフォルト値を設定: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20; initial_portfolio_value は broker.get_available_cash() から取得）。
  - ExecutionEngine は pid ファイルをサポートし、停止フラグが既に立っている場合は起動をスキップする。
- 監視（Monitoring）関連を追加。
  - SystemMonitor の初期化と monitoring DB 初期化（init_monitoring_db）呼び出しを含む監視プロセス起動スクリプト。
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（0以下や不正値はデフォルト 60 秒にフォールバックし、警告ログを出力）。
  - 停止フラグ検出によりループを終了、例外はログに記録して次ポーリングを継続。
- 分析/研究用モジュールを追加（部分実装）。
  - research.factor_research: DuckDB を用いたファクター計算の枠組み（モメンタム、移動平均乖離、ATR、流動性等を想定）。（ファイル末尾で未完の実装開始を示唆する箇所あり）
- ツールを追加。
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値に基づいて PASS/FAIL を判定する。P95 計算、期間フィルタ、欠損テーブル時の堅牢性を実装。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注:
- 本リリースでは主要な機能の骨格（設定管理、起動スクリプト、ログ/プロセスユーティリティ、ポートフォリオ構築、ポジションサイズ計算、監視・検証ツール）が揃っていますが、各コンポーネント（ExecutionEngine 内部の具体的な注文処理や研究モジュールの詳細計算など）は別ファイルに実装されます。ドキュメントや設定ファイル（config/*.yaml）の生成は validate_config / config_setup を参照してください。