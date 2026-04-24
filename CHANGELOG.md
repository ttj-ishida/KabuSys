CHANGELOG
=========

すべての注目すべき変更履歴を記載します。本ファイルは Keep a Changelog の形式に準拠しています。
重要な変更（Added / Changed / Fixed / Deprecated / Removed / Security）を日本語で記載しています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（今後の変更をここに記載してください）

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリース。KabuSys の基幹機能群を追加。
- 環境/設定関連
  - Settings クラスを実装。環境変数から各種設定（J-Quants / kabuAPI / DBパス / PAPER_TRADING / 監視閾値 / 実行環境 等）を取得するプロパティを提供。
  - 自動 .env ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。読み込み順: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パース強化: export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱いなどを実装。
- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を初期作成/更新するツールを追加。項目定義、既存値の読み込み、シークレット値のマスク表示、保存確認を実装。
  - validate_config: 起動前に環境変数や config/*.yaml の存在や基本整合性を検証するツールを追加。--strict により警告を失敗扱いにできる機能を実装。
  - tools.paper_verification_report: Paper Trading 用 SQLite DB を解析し稼働率／注文成功率／送信率／遅延（P95など）に基づく検証レポートを生成するスクリプトを追加。期間フィルタ、デフォルト DB パスの解決 (--db / 環境変数) に対応。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と分離。BrokerClientFactory 経由のブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、スレッドでのエンジン実行、stop flag / pid ファイルの扱い等を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
- ロギング / プロセス管理
  - utils.logging_setup.setup_logging: stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一的に設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は警告ログを出して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（既存保有を考慮して新規候補を除外）とレジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マッピング）を実装。未知のレジームは警告後 1.0 でフォールバック。
  - portfolio.position_sizing: position sizing ロジックを実装。allocation_method="risk_based" / "equal" / "score" をサポート。損切り・リスク比率に基づく計算、単元株（lot_size）での丸め、aggregate cap（合計コストが available_cash を超える場合のスケールダウン）と残差処理ロジック（fractional remainder に基づく追加配分）を実装。cost_buffer による保守的なコスト見積りにも対応。
- research.factor_research: ファクター計算の骨組み（モメンタム等）を追加（DuckDB を使った prices_daily / raw_financials ベースの計算を想定）。（一部実装ファイル内で未完の箇所あり）

Changed
- （該当なし: 初回リリースのため過去の変更はありません）

Fixed
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化。環境変数が不正（非整数 / 0 以下）の場合は警告を出しデフォルト値（60 秒）にフォールバックする実装を追加。
- .env 読み込み時のエラーでの警告出力を改善（読み込み失敗時に warnings.warn を使用）。
- ログ出力を stdout に統一（cron / タスクスケジューラからのリダイレクト運用を考慮）。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup のテンプレートに明記。
- Settings の必須プロパティは未設定時に ValueError を投げることで起動時に明確に失敗させる設計。validate_config による事前チェックを推奨。

Notes / その他
- run_monitoring は監視用 DB の初期化（init_monitoring_db）や duckdb との接続を行うため、実行環境での DB ファイルパス設定（環境変数 DUCKDB_PATH / SQLITE_PATH）を事前に確認してください。
- run_execution は paper_trading モードで本番 DB と分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。paper_trading 用の挙動は MockBrokerClient を含む形で想定されています。
- 一部モジュール（例: research.factor_research）は計算ロジックが続く想定でファイルの途中まで実装されています。今後のリリースで追加実装・テストが必要です。

Authors and acknowledgement
- KabuSys チーム（コードベースから推測して自動生成）

----- End -----