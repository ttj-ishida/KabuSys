# CHANGELOG

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-25
初回リリース。システム全体の基礎機能を実装しました。

### Added
- 基本パッケージ情報を追加（kabusys.__version__ = 0.1.0）。
- 設定/環境読み込み
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env, .env.local の読み込み順をサポート。OS 環境変数は保護（上書き防止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、閾値、環境種別など）を取得可能に。
  - 環境変数のパースはクォート/エスケープ/コメント対応。

- 設定支援 CLI / 検証ツール
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パス存在チェック、YAML のパース検証（PyYAML が存在する場合）などを実行可能。--strict モードをサポート。

- 実行エンジン / 監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db など）を使用し MockBrokerClient を利用する仕様を想定（BrokerClientFactory を介して切替）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てと起動ロジックを実装。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による停止検知と安全停止処理を実装。実行用 PID ファイル出力の仕組みを導入。
    - init_monitoring_db を呼び出して監視テーブルが存在することを冪等的に保証。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する仕様。
    - stop flag（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt もハンドル。

- 監視 DB 初期化
  - monitoring_db 初期化関数（init_monitoring_db）を利用して監視用テーブルの存在を保証。

- ロギング / プロセス制御ユーティリティ
  - setup_logging: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決・ディレクトリ作成に対応。既存ハンドラをクリアして多重設定を防止。
  - process_priority: set_process_priority と set_cpu_affinity を実装。Windows / POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築モジュール（純関数群・DB 参照なし）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存ポジションのセクター別時価を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告のうえ 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を算出。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）超過時のスケーリング、cost_buffer を考慮した保守的見積り、残余に対する再配分ロジックを実装。

- ツール
  - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプトを実装。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - P95 計算ユーティリティ実装、日付フィルタ（--from / --to）、DB パスの CLI/環境変数解決をサポート。
    - しきい値（稼働率 99% など）を定義。

- 研究用モジュール（骨組み）
  - research/factor_research: DuckDB ベースでファクター（Momentum, Value, Volatility, Liquidity）を計算するモジュールの骨組みを追加（momentum 計算関数等を開始実装）。DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する設計。

### Changed
- ログ出力先を stdout に統一するハンドラを設け、cron/スケジューラからのリダイレクトを考慮。

### Fixed
- MONITOR_POLL_INTERVAL やその他環境変数の不正値に対して明確にフォールバックし、例外を未然に防止。

### Security
- config_setup で生成される .env に関して「絶対に Git にコミットしないこと」を明記。
- Settings._require による必須環境変数の未設定時は ValueError を送出。

### Notes / Known issues / TODO
- apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨をログに注記。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - 将来的な拡張として銘柄別の lot_size（マスタ）をサポートする予定（現在は全銘柄共通の lot_size）。
- research/factor_research:
  - 一部関数の実装が続き（ファイル末尾で途中切れ）、今後の補完が必要。
- run_monitoring は monitoring 用 DB として常に本番 sqlite_path を使う設計。意図的な仕様のため変更に注意。
- process_priority / set_cpu_affinity は権限や OS により動作しない場合がある（権限エラーは警告でスキップ）。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の完全実装と単体テスト
- ExecutionEngine / RiskManager / BrokerClient の統合テスト強化
- エラー通知（LINE）やアラートルールの拡充
- 単体テストと CI 設定の強化

（以上）