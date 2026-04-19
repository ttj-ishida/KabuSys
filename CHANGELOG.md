CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

フォーマットのルール:
- 重要・利用者向けの変更をカテゴリ別に記載（Added, Changed, Fixed, Deprecated, Removed, Security）
- 日付はリリース時の日付を使用

[Unreleased]
------------

（現在のコードベースは最初の公開リリース相当のため、主要な変更は下の 0.1.0 にまとめられています。今後の変更はここに記載します。）

0.1.0 - 2026-04-19
------------------

Added
- 初期公開: KabuSys 自動売買フレームワークの基本機能を実装。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。Paper Trading（KABUSYS_ENV=paper_trading）時は MockBrokerClient を使用し、paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）を用いることで本番 DB と分離。
  - run_monitoring.py: SystemMonitor 起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用の sqlite_path を用いる設計。
- 設定管理
  - config.py: .env 自動読み込み（.env, .env.local をサポート、OS 環境変数保護機能あり）、環境変数アクセス用 Settings クラスを実装。環境切替フラグ（development / paper_trading / live）や多数の設定プロパティ（DB パス、PID / Kill flag パス、閾値等）を提供。
  - config_setup.py: .env 作成・更新の対話式ウィザードを実装（必須/任意項目、シークレット入力、保存機能）。
  - validate_config.py: 起動前の設定検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、--strict オプション対応）。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等金額・スコア加重配分を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score の allocation_method、lot_size 単位丸め、aggregate cap によるスケーリング等）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/__init__.py で API をエクスポート。
- 監視・実行支援
  - utils/logging_setup.py: StreamHandler（stdout）＋日次ローテーションの TimedRotatingFileHandler を統一的に設定するユーティリティを実装。ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解釈、既存ハンドラのクリア等に対応。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定・CPU affinity ユーティリティを実装。アクセス権限不足や未対応 OS を考慮したフォールバック対応あり。
- 実行エンジン周辺コンポーネント（参照実装）
  - execution 以下で BrokerFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てと起動処理を実装（run_execution.py から起動）。
  - monitoring.monitoring_db.init_monitoring_db を用いて監視用テーブルの冪等初期化を実施。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを実装。稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
- 研究用モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算基盤（モメンタム、MA200、ATR、流動性等）を設計・実装（DuckDB 接続を受け取って prices_daily / raw_financials を参照する方針）。

Changed
- なし（初回リリース）

Fixed
- 環境ファイルパーサーの改善（config._parse_env_line）
  - export プレフィックス対応、クォートのエスケープ処理、インラインコメントの扱い、クォート無し値のコメント判定等を精緻化。
- ロギングハンドラの二重設定防止: setup_logging は既存ハンドラを flush/close してから削除するように変更（重複出力を回避）。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の読み書き・表示上の配慮
  - config_setup のシークレット項目は表示時にマスク（****）して表示。
  - .env を Git にコミットしない旨を README/生成ヘッダに明記（config_setup が .env ヘッダを出力）。

Notes / Usage highlights
- 起動方法
  - 監視: python -m kabusys.run_monitoring
  - 実行: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境関連
  - .env 自動ロードはデフォルトで有効。プロジェクトルートは .git または pyproject.toml によって探索される。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - KABUSYS_ENV により動作モードを切替（development / paper_trading / live）。paper_trading は発注を分離して専用 DB に記録する。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を秒単位で指定可能（デフォルト 60）。0 以下や不正値は無視され、デフォルトにフォールバックする。
  - PAPER_FILL_MODE（instant|partial|never|reject）でペーパートレードの約定挙動を指定。
  - 実行・監視の停止はプロジェクトルート/data/stop_requested.flag や kill.flag 等のフラグファイルによって制御。

Known limitations / TODOs
- 一部モジュール（研究用ファクター計算など）は DuckDB 上のテーブル構造に依存。データ準備用のスクリプト/マイグレーションは別途必要。
- position_sizing の lot_size は現状全銘柄共通の固定値（将来的に銘柄別対応を予定）。
- apply_sector_cap は price の欠損時に過小評価になる可能性があり、フォールバック価格の検討を TODO として残している。

References
- 本 CHANGELOG はソースコード（src/ 以下）の実装に基づき作成しました。実際のリリース時はリリース日・変更点を都度更新してください。

[Unreleased]: #unreleased
[0.1.0]: #010---2026-04-19