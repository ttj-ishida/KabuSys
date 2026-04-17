# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。複数バージョンがある場合は上から新しい順に記載します。

全般的な注記:
- 本リリースは初期公開バージョンです。
- CLI はモジュール実行（python -m kabusys....）で利用可能なエントリポイントを多数提供します。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 基本機能
  - パッケージ初期リリース。
  - バージョン情報を `kabusys.__version__ = "0.1.0"` として公開。

- 設定・環境読み込み
  - .env 自動ロード機能を追加（プロジェクトルート (.git または pyproject.toml) を探索して .env/.env.local を読み込む）。
  - .env パーサ実装を追加（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを実装し、環境変数経由でアプリケーション設定を取得可能に（J-Quants / kabuAPI / DB パス / モード判定等）。
  - PAPER_FILL_MODE/SQLITE_PATH/DUCKDB_PATH 等の環境変数サポートと妥当性チェックを追加。

- 設定支援ツール
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（python -m kabusys.config_setup）。
  - validate_config: .env および config/*.yaml の事前検証 CLI を追加（python -m kabusys.validate_config）。--strict オプションで警告を失敗扱いに可能。
  - validate_config は PyYAML の有無を考慮し、ファイルの存在／YAML パース検証・本番環境のガード（LINE通知・Kill Flag 設定等）を行う。

- 実行 / 監視用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB を分離して利用。
    - エンジンは ExecutionEngine.run_session をスレッドで実行し、 data/execution.pid に PID を書き出す仕組みを想定。
    - BrokerClientFactory により本番／モックの切替えを実現。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。initial_portfolio_value を broker.get_available_cash() で初期化。
    - 停止フラグ (data/stop_requested.flag) を監視し、安全に停止するロジックを追加。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - プロセス優先度を起動時に "high" に設定（utils.process_priority 経由）。
    - 監視処理中の例外を捕捉してログ出力し、次ポーリングへフォールバックする堅牢化ロジック。
    - 監視 DB 初期化（init_monitoring_db）を行い、監視テーブルの存在を保証（環境に関わらず本番 sqlite_path を使用する挙動を明記）。

- データベース・分析
  - DuckDB / SQLite の接続サポートを追加（Settings がパスを提供）。
  - init_monitoring_db により監視用テーブルが存在することを保証（冪等）。

- ポートフォリオ構築モジュール
  - portfolio_builder: シグナル選定（select_candidates）、等重み配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等重みへフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。
    - apply_sector_cap は既存保有と当日売却予定を考慮してセクター別エクスポージャーを算出し、閾値を超えるセクターの新規候補を除外（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をマップし、未知のレジームは 1.0 でフォールバック（警告）。
  - position_sizing: position サイズ計算（calc_position_sizes）を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、max_position_pct（銘柄上限）、max_utilization（総資金利用率）を考慮。
    - cost_buffer を考慮した aggregate cap スケーリング実装（スケールダウン → 余剰キャッシュで残差に基づく lot 単位の追加配分）。
    - 価格欠損時のスキップやログ出力などの堅牢化。
  - portfolio パッケージ __init__ で主要関数をエクスポート。

- 研究用関数
  - research.factor_research: DuckDB を用いたファクター計算モジュールを追加（モメンタム/ボラティリティ/流動性等の計算）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None を許容）。
    - calc_volatility: ATR・相対ATR・20日平均売買代金・出来高比などを計算（ウィンドウ不足時は None）。
    - DuckDB 内でウィンドウ関数を多用する SQL ベースの実装。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し、閾値に基づく PASS/FAIL 判定を実施。
    - CLI オプション --from/--to/--db を提供。P95 計算の実装と各種 SQL クエリを用いた堅牢な取得ロジック。

- ユーティリティ
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定を追加（psutil を利用、Windows/Linux/Mac 対応を吸収）。
    - set_process_priority(level) は cross-platform に対応し、権限不足や非対応環境では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) により先頭 N コアへ固定可能（不足時は全コア使用）。

Changed
- なし（初期リリースのため、過去の挙動からの変更はなし）。

Fixed
- .env 読み込み時のエスケープ・クォート処理やインラインコメントの取り扱いを慎重に実装し、誤読のリスクを低減。
- run_monitoring/run_execution の終了処理で DB 接続を確実にクローズするよう設計。
- MONITOR_POLL_INTERVAL に不正な値が設定された場合のフォールバック処理を追加（無効値で ValueError が発生するのを防止）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

補足（運用上の注意）
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用します（KABUSYS_ENV に依存しない点に注意）。
- run_execution は paper_trading 環境時に paper_trading 用 DB を利用して本番 DB とデータを完全分離します。
- .env は絶対に Git にコミットしないでください（config_setup にも注意書きを記載）。
- 本番運用時は KABUSYS_ENV=live の設定と LINE 通知の設定、KILL_FLAG_CLEAR_ON_START の値等を十分確認してください（validate_config にて警告・チェックあり）。

----- 

今後の予定（例）
- 銘柄ごとの lot_size を外部マスタから読み込む拡張（position_sizing の TODO）。
- 価格欠損時のフォールバック（前日終値や取得原価）を導入し、エクスポージャーの過少評価を改善。
- 追加の監視メトリクス／アラート機能強化（LINE 通知連携等）。