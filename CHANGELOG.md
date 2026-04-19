# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19
初回リリース。コードベース全体を初期実装しました。主な追加点と動作の要点は以下の通りです。

### Added
- 全体
  - パッケージ初期実装。パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - DuckDB / SQLite を併用したデータ層のサポート（設定によりパス指定可能）。
  - .env ファイルの自動読み込み（プロジェクトルート検出ロジックを含む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

- 起動スクリプト / CLI
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用の `sqlite_path` を使用（明示的な分離要件）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループを終了。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を選択し、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中は PID ファイルを扱い、停止フラグによりエンジンを停止する仕組みを実装。
  - validate_config: 起動前に .env と config/*.yaml の不足を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、
      YAML パース（PyYAML がインストールされていれば内容検証を実施）を含む。
    - `--strict` オプションで警告も失敗扱いにできる。
  - config_setup: .env を対話的に作成／更新するウィザードを追加。
    - J-Quants / kabu API 等の主要設定項目を対話式に入力・確認し .env を生成するユーティリティ。
  - tools.paper_verification_report: ペーパートレード用検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均 / 最大 / P95）などを集計・判定。
    - レポートに使用するしきい値（稼働率 99% 等）を定義し PASS/FAIL 判定を行う。

- コンフィグ管理
  - `kabusys.config.Settings` 実装:
    - J-Quants / kabu API / LINE / DB パス / 各種閾値 / 環境識別（development / paper_trading / live）などをプロパティで取得。
    - `PAPER_FILL_MODE`（instant/partial/never/reject）や `PAPER_TRADING_SQLITE_PATH` をサポート。
    - 各種妥当性チェック（env 値や log level の検証）を実装。
  - .env のパースと読み込み
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応する堅牢なパーサを実装。
    - .env, .env.local の読み込み順を定義し OS 環境変数を保護する仕組みを実装。

- ポートフォリオ／戦略関連（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソートと上位選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコアが0の際は等分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価合計を用いて上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数の計算。
    - 単元（lot_size）丸め、ポジション上限、aggregate cap によるスケールダウン、コストバッファ考慮、残差を使った追加配分アルゴリズムなどを実装。

- 実行系インフラ
  - execution サブモジュール（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）の骨格を組み、ExecutionEngine が起動できる構成を用意。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定し、初期化時に broker の現金を使用して initial_portfolio_value を設定する設計。

- ログ・プロセス管理ユーティリティ
  - utils.logging_setup: 統一的なログ設定を提供。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバック実装。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン固定（利用可能コア数チェック・例外ハンドリングあり）。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の利用を通じ、監視テーブルの存在を保証（冪等）。

- 研究用モジュール（research）
  - factor_research: モメンタム等のファクター計算基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを構築する方針）。
    - モメンタム（1M/3M/6M）、MA200 乖離率、ATR/ボラティリティ/流動性等を計画。calc_momentum 関数の設計方針を実装開始（関数の冒頭が含まれる）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 初期リリースではセキュリティ関連のハードニングは限定的。  
  - .env ファイルに秘密情報を記載する設計のため、`.env は絶対に Git にコミットしないこと` を README / config_setup のヘッダで強調。

### Notes / 実運用上の注記
- run_monitoring は Monitoring 用に常に本番用 sqlite_path を使用する設計になっているため、テスト/開発環境で監視 DB を完全に分離したい場合は sqlite_path を明示的に設定する必要があります。
- run_execution は paper_trading モード時に paper_sqlite_path を使用し本番 DB と分離するため、ペーパートレード結果は本番 DB に混ざりません。
- process_priority・CPU affinity の設定は OS / 権限に依存し、失敗した場合は警告を出して安全にスキップします。
- config_setup / validate_config により起動前に設定不備を検出できるため、本番導入時はこれらを CI や運用手順に組み込むことを推奨します。
- research.factor_research 等は DuckDB や prices_daily/raw_financials のスキーマに依存します。実データの投入・テーブル作成手順をドキュメント化することを推奨します。

もし changelog に含めたい追加の視点（例えば重要なファイルごとの変更点や更に詳細な実装メモ）があれば教えてください。コードの他ファイル（未提示の execution 実装詳細や monitoring の内部実装など）に基づいてさらに細かく記載できます。