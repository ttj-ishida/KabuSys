# CHANGELOG

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased
-----------------

### Added
- research.factor_research モジュールにファクター計算基盤を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。※一部実装が作業中（calc_momentum の実装開始箇所が未完）。
- テスト用・解析用のユーティリティや CLI 用のフック（report 生成・検証用）を追加予定。

### Known issues / TODO
- calc_momentum の実装はファイル末尾で途中（start_da で途切れ）になっているため、完全なファクター計算ロジックは未完成。
- 追加テスト・ドキュメント整備が必要。

0.1.0 - 2026-04-23
------------------

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを導入。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境変数 KABUSYS_ENV による paper_trading モードをサポートし、paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag により制御。
- 設定関連
  - config.py: 環境変数の読み込み／管理を行う Settings クラスを追加。.env 自動読み込み（.env → .env.local、OS 環境優先）や .env のパースロジックを実装（export 形式・クォート・コメントの扱いに対応）。各種設定プロパティ（DB パス、ログレベル、ペーパートレード設定等）を公開。
  - config_setup.py: 対話式の .env 作成／更新ウィザードを追加。主要項目（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL、Kill Switch など）をガイドして .env を生成。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの確認、YAML ファイルのパース検証（PyYAML がある場合）や本番時の追加ガードを実装。--strict オプションで警告を失敗扱いにできる。
- Execution / Order 管理基盤
  - execution パッケージの骨格（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を利用する起動フローを run_execution.py で組み立て。RiskManager にデフォルトの RiskConfig を与え、initial_portfolio_value をブローカーの利用可能現金から取得する仕様を導入。
  - ExecutionEngine は別スレッドで run_session を実行し、stop flag を監視して安全に停止できる制御を実装。PID ファイルの管理を考慮（_EXECUTION_PID）。
- 監視（Monitoring）
  - monitoring 用 DB 初期化関数 init_monitoring_db の呼び出しを起動時に実行し、監視テーブルの存在を担保。
  - run_monitoring.py は SystemMonitor を用いて定期チェック（monitor.check_once）を実行し、例外発生時もログを残してポーリングを継続する堅牢なループを実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合のフォールバック警告あり。
  - portfolio.risk_adjustment: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。regime に対するデフォルトマップと未知レジームのフォールバックを提供。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に基づく発注株数計算を実装。単元株（lot_size）丸め、per-position および aggregate の上限、cost_buffer による保守的見積り、available_cash に基づくスケーリングと残差を考慮した追加配分ロジックを実装。
  - portfolio パッケージ __all__ に主要関数をエクスポート。
- ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせる。既存ハンドラの重複防止、ログディレクトリ作成のフォールバック、環境変数や引数からのログレベル/ログディレクトリ解決をサポート。ログ出力は stdout を使用（cron 等でのリダイレクトを想定）。
  - utils.process_priority: Windows / POSIX の差を吸収したプロセス優先度設定と CPU affinity 設定を提供。アクセス権限などで失敗した場合は警告を出してスキップする堅牢設計。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可能）を解析して検証レポートを標準出力に出す CLI を追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を計算し、閾値（稼働率99%、成立率90%、送信率95%、P95 latency 200ms）で PASS/FAIL 判定を行う。SQL 結果が存在しない場合やテーブルが欠落している場合のフォールバック処理あり。
- パッケージメタ情報
  - kabusys.__init__ に __version__ = "0.1.0" を追加。

### Changed
- 初期リリースのため、既存変更はなし（新規導入）。

### Fixed
- 初回リリースのため、バグ修正履歴はなし。

### Security
- 機密情報（API トークン・パスワード）は .env に保存する前提で、config_setup はシークレット入力をマスク（表示は ****）して確認画面を行う設計。

補足／設計上の注意
- .env の自動ロードはデフォルトで有効。テストや特殊ケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring は Monitoring 用 DB に常に本番 sqlite_path を使用する（環境に依らない）。run_execution は paper_trading 環境では paper_sqlite_path を使用して DB を分離する。
- ロギングは stdout をメインに出力するため、外部のログ集約（systemd / cron のリダイレクト）と相性が良い。
- process_priority/CPU affinity の設定は権限不足や未対応 OS の場合に安全にスキップする挙動。

開発メモ（参考）
- research/factor_research の完全実装、config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）の追加、単体テスト・CI 設定、ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）の参照実装を今後追加予定。

--- 

（以降のリリースはここに追記してください）