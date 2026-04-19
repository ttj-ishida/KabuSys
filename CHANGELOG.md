CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは、コードベース（現行スナップショット: バージョン 0.1.0）から推測される機能追加・改善点・修正を基に作成しています。

Unreleased
----------
- なし（現時点で未リリースの変更はありません）。

[0.1.0] - 2026-04-19
-------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" の基礎機能群を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- コマンドライン / 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV に応じて paper_trading 用のモックブローカーと専用 SQLite（data/paper_trading.db）を使用可能。PID ファイル・停止フラグをサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。監視は環境に関係なく本番 sqlite_path を使用。
  - validate_config: .env と config/*.yaml の設定検証 CLI を追加。必須環境変数確認、KABUSYS_ENV／LOG_LEVEL チェック、DB パスと YAML ファイルの存在・パース検証、live 環境向けのガード確認を実施。--strict オプションで警告を失敗扱いにできる。
  - config_setup: 対話式の .env 作成/更新ウィザードを追加。シークレット入力や選択肢、既存値の再利用・確認・保存をサポート。
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し PASS/FAIL 判定を出力。

- 設定・環境読み込み
  - config.Settings: 環境変数ラッパーを実装。duckdb/sqlite パス、paper_trading 用パス、各種しきい値、PID パスや Kill フラグ等をプロパティで提供。
  - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込み。OS 環境変数は保護（.env.local は上書き可能だが保護されたキーは上書きされない）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ: export KEY=val, クォート文字列、バックスラッシュエスケープ、インラインコメント処理などに対応した堅牢なパーサを実装。

- データベース・永続化
  - monitoring 用 SQLite（SQLITE_PATH）と分析用 DuckDB（DUCKDB_PATH）をサポート。monitoring の初期化（init_monitoring_db）を行い、監視テーブルの存在を保証。
  - Paper Trading 用に PAPER_TRADING_SQLITE_PATH を分離（本番 DB と完全に分離）。

- ロギング & 運用ユーティリティ
  - utils.logging_setup.setup_logging: stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力する。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。CPU affinity 設定関数も提供。アクセス権限等で失敗した場合は警告を出してスキップ。

- Execution コンポーネント（概念的追加）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の構成に対応する起動フローを整備（run_execution での組み立て確認）。
  - RiskManager の初期設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を追加し、初期ポートフォリオ価値をブローカーから取得して設定。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）にソートして上位 N を返す。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコアに基づく配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）と新規候補の除外ロジックを実装。売却予定銘柄の除外や unknown セクター扱いが可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。stop_loss, risk_pct, max_position_pct, max_utilization, lot_size（単元株丸め）、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケールダウンと残差配分ロジックを実装。

- リサーチ（計算モジュール）
  - research.factor_research（モジュール追加、モメンタム等の計算を実装予定）
    - モメンタム計算のための定数（1M/3M/6M、MA200、ATR 等）と calc_momentum の雛形を追加（DuckDB 接続を受け取り prices_daily 等のテーブルから計算する設計）。

- ツール / レポート
  - paper_verification_report: 実行可能な CLI を提供し、稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出。しきい値（稼働率 99%、成功率 90% 等）に基づいて PASS/FAIL を判定。

Changed
- なし（初期リリースのため変更履歴は追加項目としてまとめられています）。

Fixed
- なし（初回リリース時点で既知のバグ修正履歴はありませんが、各所でエラー発生時の安全なフォールバックや警告ログ出力を実装）。

Security
- なし（セキュリティ脆弱性の修正は記録なし）。

Deprecated
- なし。

Removed
- なし。

Notes / 運用上の注意
- .env ファイルは絶対にリポジトリへコミットしないこと（config_setup のヘッダにも明記）。
- run_monitoring は監視用 SQLite（settings.sqlite_path）に常に接続します。paper_trading と本番 DB の分離に注意してください（run_execution は環境に応じて paper 用 DB を使用）。
- process_priority や CPU affinity は実行環境の権限に依存します。権限不足時は警告ログが出力され、処理は継続されます。
- paper_verification_report の P95 計算はサンプルベースの実装（簡易パーセンタイル）を用いています。厳密な統計要件がある場合は別実装の検討を推奨。

作者注
- 本 CHANGELOG は提供されたコードスナップショットの内容から推測して作成しています。実際のコミット履歴や開発ノートと差異がある可能性があります。必要であれば実リポジトリのコミットログを参照して正確な変更履歴へ更新してください。