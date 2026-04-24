CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-24
-----------------

Added
- 実行スクリプトを追加／整備
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離して動作。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）検知で安全にシャットダウンする仕組みを実装。PID ファイル（data/execution.pid）管理、BrokerClientFactory を利用したブローカー抽象化、OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用。停止フラグ検知でループを終了し、例外発生時はログを残して次ポーリングに継続。

- 設定・環境変数関連
  - config_setup.py: 対話式 .env 設定ウィザードを追加。キーごとに説明・デフォルト・選択肢・シークレット入力をサポートし、.env を安全に生成/更新するユーティリティを提供。
  - config.py: Settings クラスを実装。環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL 等）、デフォルト値、パス（duckdb/sqlite/paper）や paper_fill_mode の妥当性チェック、ユーティリティプロパティ（is_live/is_paper/is_dev）を提供。
  - 自動 .env ロード機構を追加: プロジェクトルート（.git または pyproject.toml を基準）を検出し、.env/.env.local を自動読み込み（OS 環境変数が優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- 検証ツール
  - validate_config.py: .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML が存在する場合）などを実行。--strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。権限不足／未対応環境でも例外を吐かず警告でスキップする。

- ポートフォリオ構築関連モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック挙動を定義。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）をサポートする株数決定ロジックを実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap、手数料/スリッページの保守的見積り（cost_buffer）に基づくスケーリングと残差処理を含む。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポートを出力するスクリプトを追加。閾値に基づく PASS/FAIL 判定を行う。

- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials を基にモメンタム等のファクターを計算するモジュールを追加（モジュール構成と設計方針を実装）。（ファイル末尾は一部切り出しあり）

Changed
- logging の既定挙動を stdout に統一（StreamHandler を stdout に設定）。cron/Task Scheduler 等でリダイレクトを扱いやすくするため。
- .env ローダー: .env.local を .env よりも優先して上書きする挙動を採用（OS の env は常に保護）。
- run_monitoring の既定ポーリング間隔を定数化（60 秒）し、環境変数で上書き可能に。無効な値は警告を出してデフォルトにフォールバック。
- validate_config: PyYAML 未インストール時は YAML 検証をスキップして警告出力するよう変更。

Fixed
- .env パーサー: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの取り扱い等を適切に処理するよう改善。これにより .env 内の複雑な値の読み込みが安定。
- logging_setup: 既にハンドラが設定されている場合に二重でハンドラが追加される問題を解消（既存ハンドラを flush/close してから削除）。
- process_priority: 未対応 OS や権限不足での例外が起きるケースを捕捉して安全にスキップするよう改善。

Notes / その他
- Settings.paper_fill_mode は有効値検証を行い、不正な値では ValueError を送出する（有効値: "instant" | "partial" | "never" | "reject"）。
- run_monitoring は監視用 DB に監視テーブルを初期化するため init_monitoring_db を利用する（冪等）。
- run_execution は停止フラグを起動前に検査し、フラグが立っている場合は起動をスキップする安全措置を実装。
- いくつかのモジュール（実行エンジン・ブローカー周りなど）は抽象化レイヤ（Factory / Manager）で分割されており、ペーパートレードと実口座の切り替えが容易に設計されている。

Deprecated
- なし

Removed
- なし

Security
- なし

リリースノートは実装ファイルから推測して作成しています。実際のリリース手順や公開日付はプロジェクトのポリシーに合わせて調整してください。