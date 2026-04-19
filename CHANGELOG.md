CHANGELOG
=========

すべての重要な変更はここに記録します。  
このファイルは "Keep a Changelog" の慣例に準拠しています。

フォーマット:
- 変更はセクションごとに分類されています（Added / Changed / Fixed / Deprecated / Removed / Security）。
- 各リリースにはバージョンと日付を付与しています。

v0.1.0 - 2026-04-19
-------------------

Added
- 初期リリース。以下の主要コンポーネントを追加。
  - 設定管理
    - kabusys.config: .env 自動ロード（.env / .env.local、OS 環境変数優先、無効化フラグあり）、プロジェクトルート探索、環境変数パーサ（クォート・エスケープ・export 対応）。
    - Settings クラス: DB パス、各種閾値、環境フラグ（development/paper_trading/live）などのプロパティを提供。
  - 起動 / 運用スクリプト
    - run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を分離し、MockBroker を利用する想定。PID ファイル、停止フラグ対応、バックグラウンドスレッドでエンジン実行。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔指定、停止フラグ対応。
  - 設定管理 CLI
    - config_setup: .env の対話式ウィザード（作成・更新）。既存値の読み取り・保存機能あり。
    - validate_config: .env と config/*.yaml の事前検証ツール。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: 候補選定、等配分・スコア加重ウェイト計算。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 対応。
    - package エクスポート (__init__.py) を整備。
  - 研究用ファクター計算基盤
    - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するための基盤（モメンタム等の定数と関数群を追加。実装途中の関数あり）。
  - ユーティリティ
    - utils.logging_setup: 統一的ログ設定（stdout StreamHandler + TimedRotatingFileHandler 日次ローテーション、ログレベル解決、ログディレクトリ作成のフォールバック処理）。
    - utils.process_priority: クロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity セット機能。権限不足時に警告でスキップ。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計して PASS/FAIL 判定を出力。--from/--to/--db オプション対応。
  - 監視 DB 初期化ユーティリティ（monitoring.monitoring_db 参照）
  - Execution 周りの基盤（order_manager, order_repository, reconciler, risk_manager の組み立てロジックを run_execution で利用）

Changed
- ロギング
  - ルートロガーを統一的に初期化する setup_logging を追加。既存ハンドラは一旦クリアしてから再設定することで二重出力を防止。
  - ストリームは stdout を使用（cron 等で stdout/stderr を一本化しやすくするため）。ログファイル出力はディレクトリ作成に失敗した場合に自動的に無効化して続行。
- 環境変数読み込み
  - .env パーサを強化（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの改善）。
  - 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- 起動時のプロセス優先度設定を統合
  - run_execution/run_monitoring の先頭で set_process_priority("high") を呼び出すようにし、実行中のプロセス優先度を可能な限り高く設定する（クロスプラットフォーム対応、失敗時は警告でフォールバック）。
- DB 周り
  - run_execution/run_monitoring は DuckDB と SQLite の両方に接続するデフォルト構成を採用。
  - 監視テーブル初期化は冪等に行う（init_monitoring_db を呼ぶことで存在を保証）。
  - paper_trading モードでは SQLite DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
- Execution エンジンの挙動
  - 停止フラグ（data/stop_requested.flag）を検知すると安全に停止する制御（起動時に既に停止フラグがある場合は起動を行わない）。
  - Engine はデーモンスレッドで run_session を走らせ、メインスレッドからフラグを監視して停止処理を行う。
- Paper verification
  - レポートは P95 計算／閾値チェックを行い、わかりやすい PASS/FAIL と詳細メトリクスを標準出力に出力する。

Fixed
- 設定検証（validate_config）
  - 必須環境変数の未設定をエラーとし、プレースホルダ値（例: *_here / your_value）を警告として検出するロジックを追加。
  - PyYAML が未インストールでも動作するようにし、YAML の検証はインポート可能な場合のみ行う（未インストールの場合は警告を出す）。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックを追加。
- ポートフォリオ・ウェイト計算
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合は等分配へフォールバックし、警告を出す。
- position_sizing のスケーリング
  - aggregate cap によるスケールダウン時に単元株（lot_size）丸め、残余キャッシュで端数を大きい順に割り振るロジックを導入してより安定した資金配分を実現。
- logging_setup の堅牢性向上
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合に、コンソール出力のみで継続するよう修正（例外を止める）。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 使用例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（例）:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

補足
- この CHANGELOG は提供されたコードベースからの挙動・追加機能を推測して作成しています。内部の細かい実装（ExecutionEngine / BrokerClientFactory 等の詳細）は別モジュールに依存しているため、本稿ではエントリポイント側の変更点・機能を中心に記載しています。