# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。重要な変更、追加、修正点を日本語で記載しています。

フォーマットに関する簡単な説明:
- 重要な変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）でまとめています。
- 各リリースには日付を付与しています（今回のコードベースから推測した初回公開相当のバージョンを記載）。

## [Unreleased]
- 現時点で未リリースの作業はありません。

## [0.1.0] - 2026-04-24
初期リリース相当。以下の機能群、ユーティリティ、CLI、ポートフォリオ構築ロジック、監視/実行スクリプト等を実装／提供します。

### Added
- 実行および監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用スクリプトを提供。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し MockBrokerClient を利用することで本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor を定期ポーリングで実行する監視用スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB に蓄積）。

- 設定関連
  - config.py: .env の自動読み込み、堅牢な .env パーサ（export プレフィックス、引用符のエスケープ、インラインコメント処理等に対応）、Settings クラスによる環境変数アクセスラッパーを実装。PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START、各種閾値などの設定プロパティを追加。
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を提供。必須項目のマスク表示やデフォルト値、説明文を含む対話を行い .env を生成。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数・KABUSYS_ENV の妥当性・YAML 設定ファイル存在確認等）。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティ。ログディレクトリの自動作成、LOG_LEVEL/LOG_DIR の解決順を実装。ファイル書き込みエラー時はコンソール出力のみで継続。
  - utils/process_priority.py: Windows / POSIX の差異を吸収してプロセス優先度（high/normal/low）や CPU affinity を設定するユーティリティを追加。権限不足時は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分の実装（全スコアがゼロの場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック（売却予定銘柄の除外や unknown セクター扱いルール）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金の乗数を提供（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、lot（単元株）丸め、max_position_pct/aggregate cap のスケーリング、cost_buffer を考慮した保守的な見積り、残差処理による追加配分ロジックを実装。

- Execution コンポーネントの組み立て
  - run_execution では OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て例を示し、RiskConfig／EngineConfig のデフォルトパラメータ（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を設定して起動するワークフローを提供。

- 監視 DB 初期化（冪等）
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して監視テーブルの存在を保証（存在しない場合の初期化を想定）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間指定で集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行うレポートを生成。デフォルト閾値 (uptime 99.0%, fill 90.0%, send 95.0%, P95 latency 200 ms) を設定。

- DuckDB 統合
  - DuckDB 接続を受け取る設計（duckdb_path、研究・集計モジュールでの利用想定）。research/factor_research.py は DuckDB を受け取りファクター計算を行う方針を実装（Momentum 計算の骨組みを含む）。

### Changed
- ログ出力の挙動
  - すべての起動スクリプトで setup_logging を呼び出す設計によりログ出力の方式を統一。標準出力（stdout）優先で、ファイル出力はログディレクトリ作成に成功した場合のみ有効。既存ハンドラは再設定時にクリアすることで二重出力を防止。

- 環境変数読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 監視挙動
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを保存（監視データを本番 DB に集約する設計判断）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックスのサポート、引用符付き値内のバックスラッシュエスケープ処理、インラインコメントの適切な無視など、.env ファイルのパース精度を改善。これにより複雑なシークレット値やコメントを含む .env を安全に扱えるようになった。

- プロセス優先度設定の例外耐性
  - 権限不足や未実装 API（プラットフォーム差）に対して警告を出し、動作不能でも起動継続するように変更。

### Documentation / CLI help
- 各 CLI（config_setup, validate_config, paper_verification_report）に対して Usage/Help を提供。config_setup は対話式ウィザードのヘルプと保存手順を表示。

### Security
- .env ファイルについて注意喚起を出力（.env は絶対に VCS にコミットしない旨を明示）。

### Notes / Configuration changes (重要)
- 新規/変更された主要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（検証有り）
  - PAPER_FILL_MODE: instant / partial / never / reject（paper_trading 用）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - SQLITE_PATH（デフォルト: data/monitoring.db） — 監視は本番 sqlite_path を参照
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険。デフォルト 0 を推奨）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き可能。デフォルト 60 秒）

- ペーパートレードと本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path を使用するため本番監視 DB と分離される。監視（run_monitoring）は例外的に本番 sqlite_path を使用する設計のため、運用時は監視保存先の扱いに注意。

### Known limitations / TODO（コードから推測）
- research/factor_research.py はモメンタム計算の実装開始が含まれるが（ファイル末尾で中断）、まだ完成していない可能性がある。ファクター群の完全実装・テストが必要。
- position_sizing の価格欠損時のフォールバック（コメント中の TODO: 前日終値や取得原価の使用）など、データ欠損対策が残っている。
- lot_size を銘柄別に扱う拡張や、手数料・スリッページ見積りのパラメータ調整は今後の改良対象。

---

バグ報告、改善提案、ドキュメント追記などがあれば issue を作成してください。今回の CHANGELOG はコードベースの実装内容から推測して作成しており、一部実際のコミット履歴と差異がある可能性があります。