CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（次回リリースに向けた変更はここに記載します）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基礎機能を追加。
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env のパースは export 構文、クォート、エスケープ、インラインコメントをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を提供。
  - Settings クラスを実装し、環境変数経由で型付きプロパティ（DBパス、ログレベル、環境種別、paper_trading 用設定等）を取得可能。
  - 環境変数の検証（未設定時の ValueError、許容値チェック）を実装。
- 設定支援ツール
  - 対話式 .env 作成・更新ウィザード（config_setup.py）を追加。シークレットのマスク表示、デフォルト値、選択肢の提示、保存処理をサポート。
  - 設定検証 CLI（validate_config.py）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在と YAML パース（PyYAML があれば）のチェックを行い、--strict モードで警告を FAIL 扱いにできる。
- 実行エントリ / ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）や PID 管理に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。Monitoring は環境に依らず本番 sqlite_path を使用する仕様。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: stdout（StreamHandler）と日次ローテートログ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバックを実装。LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を提供（"high"/"normal"/"low"）。psutil を利用し、CPU affinity 設定関数も提供。アクセス権限不足時は安全にスキップして警告出力。
- ポートフォリオ構築モジュール（純関数群）
  - portfolio.portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が0の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。既存保有や売却予定を考慮したセクター露出計算、unknown セクターは上限適用を行わない設計。未知レジームはフォールバックして警告を出力。
  - portfolio.position_sizing: allocation_method ("risk_based", "equal", "score") に基づく株数決定ロジックを実装。損切り・リスク許容率に基づく risk_based、重みを用いる equal/score、単元株（lot_size）丸め、1銘柄上限・総投下上限の適用、コストバッファを考慮した aggregate cap のスケーリングと残差処理を実装。
- データベース / 分析
  - DuckDB と SQLite を併用する設計を導入（設定によりパス指定）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）を参照して起動前に監視テーブルの存在を担保。
- Paper Trading 向け検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を表示。閾値はソース内で明示（稼働率 99%、成功率 90% 等）。日付フィルタ、DB パス指定オプションをサポート。
- 研究 / ファクター計算（骨組み）
  - research.factor_research にてモメンタム等のファクター計算モジュールの骨子を追加（DuckDB 接続を受け取り prices_daily/raw_financials を用いる設計）。（注: ファイル途中まで実装）

Changed
- プロジェクトルート検出ロジックを __file__ ベースで行うことで CWD に依存しない動作に変更。
- ログは stdout ベースとし、cron/Task Scheduler 環境での扱いを考慮（stderr ではなく stdout を使用）。

Fixed
- .env の読み込み時の I/O エラーを警告に変換して起動継続可能に変更（tests / CI 等での堅牢性向上）。
- ログハンドラが二重に登録される問題を防止するため、setup_logging で既存ハンドラを閉じてクリアするように修正。

Security
- .env のデフォルト作成テンプレートに対して「絶対に Git にコミットしない」旨を明記。
- シークレット項目はウィザードと確認表示でマスクされるように実装。

Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL が不正（非整数や <=0）の場合、デフォルト 60 秒にフォールバックして警告を出す実装。
- run_execution は停止フラグを確認し、既に立っている場合は起動を行わない安全策を導入。実行スレッドはデーモン化され、外部からの停止要求で engine.stop() を呼ぶ。
- Settings の env/log_level などは許容値チェックを行い不正値で ValueError を投げるため、validate_config で事前確認が推奨される。
- process_priority と CPU affinity の呼び出しは権限不足や未サポート環境で失敗しても例外を外に出さず警告で済ませる堅牢設計。

Acknowledgements
- 本リリースはフレームワークの基盤実装に注力しています。今後のリリースでファクター計算の完成、ExecutionEngine / SystemMonitor の詳細実装、単体テスト・統合テストの追加、ドキュメント拡充を予定しています。