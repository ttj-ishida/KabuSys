# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

- 変更は重要度順に分類しています: Added, Changed, Fixed, Removed, Security
- 日付はリリース日を示します。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

Added
- 初回公開リリース。KabuSys の基本機能を実装・提供。
- アプリケーション構成と環境変数管理
  - Settings クラスを提供し、環境変数経由で各種設定を取得可能（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パース実装: export 形式、シングル/ダブルクォート・エスケープ、行内コメントの扱いに対応。
  - PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH 等のデフォルトパスを提供。

- CLI ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成・更新するスクリプトを追加。機密項目はマスク表示、.env に保存するテンプレートを出力。
  - validate_config: 起動前チェックツールを追加。必須環境変数チェック、KABUSYS_ENV 値チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml 存在および（PyYAML が存在すれば）パース検証、KABUSYS_ENV=live 時の追加警告を行う。--strict オプションで警告を失敗扱いにできる。

- 実行用スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動・監視（stop flag / pid ファイル管理）を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）を設定し、初期 portfolio value を broker.get_available_cash() から取得。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視用 DB（SQLite）は環境に関わらず設定された sqlite_path（本番 path）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- ロギングとプロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーを統一設定するユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定。LOG_DIR の自動作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX に対応し、権限不足等は警告ログでフォールバック。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート、上位 N を選出。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重による重み計算（スコア合計 0 の場合は等配分にフォールバックして WARNING）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を制限するフィルタ。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じて発注株数を算出（risk_based / equal / score）。lot_size（単元株）処理、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（スケーリング）を実装。端数配分は残差に基づき lot_size 単位で追加配分。

- リサーチ / ファクター計算
  - research.factor_research モジュールを追加（モメンタム計算などを想定）。設計上 DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照し、各種ファクターを出力する想定（calc_momentum 実装の骨組みあり、一部未完）。

- ツール
  - tools.paper_verification_report: ペーパートレード DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、シグナル精度、API レイテンシ等を集計してレポートを出力。閾値に基づく PASS/FAIL 判定（稼働率、fill_rate、send_rate、P95 レイテンシ）。P95 計算関数を実装。

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Security
- config_setup にて .env コメントヘッダを追加し「.env は絶対に Git にコミットしないこと」を明記。

Removed / Deprecated
- なし（初回公開）

Known issues / Notes
- apply_sector_cap 内の価格欠損処理について注記あり（price が 0.0 の場合は過少評価される可能性）。将来的に前日終値や取得原価によるフォールバックを検討する TODO がある。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size をサポートする TODO がある。
- research.factor_research の calc_momentum 等は骨組みが存在するが、完全実装（スキャン開始日変換や SQL 実装の完了）が必要。
- ログディレクトリ作成やプロセス優先度設定など、環境依存で失敗する可能性がある箇所は安全にフォールバックするが、権限や環境の確認が必要。
- run_monitoring は説明書き通り「監視 DB に本番 sqlite_path を使う」設計になっているため、paper_trading 環境であっても監視用 DB の扱いに注意が必要（意図的な設計）。

開発者向けメモ
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や非標準レイアウトでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を供給してください。
- validate_config は PyYAML が無ければ YAML 内容チェックをスキップする挙動。CI 等で厳密に検証する場合は PyYAML をインストールするか、--strict と組み合わせて利用してください。

---

（注）本 CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際のリリースノートは運用上の決定やドキュメントに基づいて調整してください。