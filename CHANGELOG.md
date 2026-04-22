CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。
バージョン管理されたリリースに対して変更をまとめてください。

フォーマット:
- Added: 新機能
- Changed: 変更点（互換性に影響する可能性があるもの）
- Fixed: バグ修正
- Security: セキュリティ修正

------------------------------------------------------------
[0.1.0] - 2026-04-22
初回リリース
------------------------------------------------------------

Added
-----
- パッケージ初回実装（__version__ = "0.1.0"）。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応する堅牢なパース処理を提供。
  - Settings クラスを実装し、アプリケーション全体で共通の設定取得 API を提供。必須変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、型変換、値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を内包。

- 設定周り CLI
  - config_setup: 対話式ウィザードで .env ファイルを初期作成／更新するツールを追加。シークレット項目のマスク表示やデフォルト値、選択肢サポートあり。
  - validate_config: .env および config/*.yaml の事前検証ツールを追加。必須環境変数未設定や YAML パースエラー、起動時の警告（--strict で警告を失敗扱い）が可能。

- ログ・プロセス管理ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを実装。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。LOG_DIR 環境変数の利用、ディレクトリ作成失敗時のフォールバック対応あり。
  - process_priority: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。Windows の優先度定数や POSIX の nice 値に対応。CPU affinity をセットする set_cpu_affinity も実装（アクセス権限エラーや未対応 OS では安全にスキップ）。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用（settings.paper_sqlite_path）、Mock ブローカクライアントの利用を想定して本番 DB と完全分離。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立て、デーモンスレッドで engine.run_session を実行。data/execution.pid への PID ファイル管理、data/stop_requested.flag による外部停止フラグ対応を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告を出してデフォルト値にフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視テーブルの一貫性保持）。
    - プロセス優先度を "high" に設定、停止フラグ（data/stop_requested.flag）検知でループを終了、KeyboardInterrupt の捕捉とクリーンアップ実装。

- 監視データベース初期化
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を冪等に保証（run_execution と run_monitoring 両方で使用）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（スコア同値は signal_rank でタイブレーク）と上位 N 抽出を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告ログを出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超えている場合、新規候補から同セクターを除外するロジック。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3）と未知レジームのフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。損切り率ベースの risk-based、単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、手数料・スリッページを見積もる cost_buffer を考慮した aggregate スケーリング、残差処理に基づく追加配分アルゴリズム等を提供。

- 分析 / レポートツール
  - tools/paper_verification_report: ペーパートレーディング検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を読み込み、system_status / trade_logs / risk_logs から稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（平均・最大・P95）等を算出。
    - 閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定め、Pass/Fail 判定を出力。
    - CLI で --from / --to による日付フィルタをサポート。

- 研究モジュール（着手）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加。DuckDB を用いた Momentum / Value / Volatility / Liquidity ファクター設計方針と定数定義を含む（実装途中の関数あり）。

Changed
-------
- 初回リリースのため、互換性のある過去変更はなし。

Fixed
-----
- .env 読み込み時の細かなパース問題に対処（export プレフィックス・クォート含む行やインラインコメント処理の改善）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラを安全にスキップするよう改善。

Security
--------
- .env の取り扱いに関する注意喚起を config_setup のヘッダに明記（.env を絶対に Git にコミットしない旨）。

Notes / Usage highlights
-----------------------
- 環境変数の優先順位: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL はポーリング秒数を設定します。1 未満や非整数を指定するとデフォルト（60 秒）にフォールバックします。
- PAPER_TRADING 環境では本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- process_priority / set_cpu_affinity は権限により失敗する可能性がありますが、安全にログ警告を出して継続します。
- logging_setup は標準出力（stdout）を用いるため、cron 等で stdout/stderr を一本化している運用環境との相性を考慮しています。

今後の予定（例）
----------------
- research/factor_research のファクター計算ロジックを完成させる。
- ExecutionEngine / SystemMonitor 周りの統合テストと細かなエラー処理改善。
- 銘柄別の単元株（lot_size）や手数料モデルの拡張（stocks マスタの導入）。
- 監視アラート（LINE 通知等）の実装強化。

------------------------------------------------------------
この CHANGELOG はコードベースの現状（ソースから推測可能な実装）に基づいて作成しています。実際のコミット履歴や過去リリースノートが存在する場合はそちらを優先してマージしてください。