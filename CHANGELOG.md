# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
各項目は安定的な公開バージョン（vX.Y.Z）として記録しています。

全般:
- 日付はリリース時に追加してください。
- バージョンは `src/kabusys/__init__.py` の `__version__` を参照してください（現時点: 0.1.0）。

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 初期リリース
初版リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視ランナー、ポートフォリオ構築ロジック、設定管理、検証ツール、ペーパートレード検証レポート等を含みます。

### Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI ランナーを追加。
    - KABUSYS_ENV = paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入。
    - OrderRepository、OrderManager、RiskManager（デフォルト設定を含む）、Reconciler を組み合わせて ExecutionEngine を構築。
    - エンジンはデーモンスレッドで run_session を実行。停止フラグ（data/stop_requested.flag）検知時に安全に停止。
    - 起動時に PID ファイル（data/execution.pid）を使用。

- 監視エントリスクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングするランナーを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境に関係なく本番 sqlite_path を使用（monitoring 用テーブルの初期化 init_monitoring_db を実行）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理
  - config.py
    - .env / 環境変数から設定を読み込む Settings クラスを提供。
    - 自動 .env 読み込みをプロジェクトルート（.git / pyproject.toml）を基準に行う。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行解析で export 形式、クォート、エスケープ、インラインコメント（クォートなしで # の前がスペースの場合）に対応。
    - 各種設定プロパティ（J-Quants, kabu API, DuckDB/SQLite パス、Paper Trading 設定、監視しきい値、環境判定等）を提供。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。

- 設定ウィザード
  - config_setup.py
    - .env の対話式作成・更新ウィザードを追加。
    - 初期値、選択肢、シークレット表示（マスク）等をサポート。
    - .env の読み込み・書き込みロジックを提供（.env ファイルを Git 管理しない旨のヘッダを自動付加）。

- 設定検証 CLI
  - validate_config.py
    - 起動前に .env および config/*.yaml の欠落や不整合を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば）、本番環境向け追加警告（LINE 通知、KILL_FLAG_CLEAR_ON_START）などを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates：BUY シグナルをスコア降順・タイブレークに signal_rank を使用して上位 N 件選定。
    - calc_equal_weights：等金額配分の重み算出。
    - calc_score_weights：スコア正規化して重み算出。全スコアが 0 の場合は等配分にフォールバックし警告ログ出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap：既存保有のセクター比率が上限を超えている場合に新規候補を除外。sell_codes（当日売却銘柄）をエクスポージャー計算から除外。unknown セクターは制限適用除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマッピングと未知レジームでのフォールバックを実装）。

  - portfolio/position_sizing.py
    - calc_position_sizes：risk_based / equal / score の配分方式に対応した株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウン、cost_buffer（手数料・スリッページ見積り）を反映、スケールダウン後の端数処理（fractional 残差に基づく再配分）を実装。

  - portfolio/__init__.py にて主要関数をエクスポート。

- 研究・ファクター計算スケルトン
  - research/factor_research.py
    - DuckDB を使ったモメンタム・ボラティリティ等のファクター計算モジュール（設計方針と主要定数、calc_momentum のドキュメント）を追加（実装の続きあり）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラの flush/close 後に再設定して二重設定を防止。
    - LOG_DIR / LOG_LEVEL の環境変数を解決して使用。ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続。
    - stdout を使用することで cron 等のログリダイレクトが容易。

  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン止め。権限不足や未サポート環境は警告でスキップ。

- モニタリング DB 初期化ヘルパー
  - monitoring/monitoring_db.py の init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード SQLite DB（デフォルト: data/paper_trading.db）から期間指定で検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 基準値（閾値）を設定し PASS/FAIL 判定を行う。
    - コマンドライン引数で期間（--from, --to）と DB パス（--db）を指定可能。
    - レポートは標準出力に整形して表示。

### Changed
- n/a（初期リリースのため既存からの変更は無し）

### Fixed
- n/a（初期リリース）

### Security
- n/a

---

補足（実装上の注意点・挙動）
- run_monitoring は Monitoring 用 DB に関して「環境にかかわらず本番 sqlite_path を使用」する旨がコメントと実装に明記されています。意図的な運用方針のため、開発時に別 DB を分離したい場合は Settings の環境変数を調整してください。
- run_execution は paper_trading 環境向けに専用 DB を使用するため、本番 DB とペーパートレードデータは分離されます。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ化後に動作環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ロギング設定はログディレクトリ作成に失敗するとファイル出力を無効化してコンソール出力のみになります。起動スクリプトは setup_logging を最初に呼ぶことで一貫したログ出力を得られます。

--- 

この CHANGELOG はコードベース（src/ 以下）から推測して作成しました。実際のリリースノートや運用ドキュメントに反映する際は、必要に応じて日付・責任者・変更理由などを追加してください。