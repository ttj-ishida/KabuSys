# Changelog

すべての重要な変更は Keep a Changelog の規約に従って記載しています。  
フォーマットの意味合い（Added / Changed / Fixed / Removed / Deprecated / Security）は各セクションを参照してください。

## [Unreleased]

### Added
- 起動スクリプトを追加・整理
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はリポジトリ直下の data/stop_requested.flag ファイルで検知する。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離（data/paper_trading.db をデフォルトとする）。停止フラグと PID ファイル管理を導入。

- 環境・設定管理
  - kabusys.config: .env 自動読み込み機能（.env/.env.local）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。各種環境変数（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値など）をプロパティ経由で取得・検証する Settings クラスを提供。
  - kabusys.config_setup: .env を対話式に生成/更新するウィザード CLI を追加。既存の .env を読み込み、シークレット項目はマスク表示しつつ保存できる。

- バリデーション・診断
  - kabusys.validate_config: 起動前設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・パスの存在確認、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を行う。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - kabusys.utils.logging_setup: 共通ログ設定ユーティリティを追加。stdout に StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。LOG_DIR/LOG_LEVEL を尊重。
  - kabusys.utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加（Windows/Linux/macOS 対応を意識）。起動スクリプトでプロセス優先度を high に設定するように利用。

- Execution 周りのコンポーネント整備（実行時の依存注入を想定）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock を利用する想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てを run_execution で行う。RiskConfig にデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() を参照する。

- ポートフォリオ構築ライブラリ
  - kabusys.portfolio: 銘柄選定・重み計算・ポジションサイズ・リスク調整の純粋関数群を追加。
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（全スコア 0 の場合は等金額にフォールバック）
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた乗数）
    - position_sizing: calc_position_sizes（risk_based / equal / score の複数配分方式、lot_size 単位丸め、aggregate cap によるスケールダウン・端数配分ロジック）

- 分析 / ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（P95）を集計し、閾値 (稼働率 99%, fill 90%, send 95%, P95 200ms) に基づく PASS/FAIL 判定を出力。P95 はサンプルから計算。
  - kabusys.research.factor_research: DuckDB を用いたファクター計算モジュール（モメンタム等）を追加（prices_daily / raw_financials を参照する設計）。

### Changed
- DB の扱いの明確化
  - 監視（monitoring）用途の DB は環境にかかわらず sqlite_path（本番設定）を使用する設計に変更。Paper Trading 実行時のみ paper_sqlite_path を使用して本番 DB と分離。

- ロギングのデフォルト挙動
  - ログ出力は stdout を使用するよう明記（cron/Task Scheduler などで stdout/stderr を一本化する運用を想定）。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを導入。

### Fixed
- 環境ファイルのパース強化
  - .env パーサ `_parse_env_line` を実装し、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。これにより .env の柔軟な記述を許容。

### Notes / WIP
- factor_research モジュールは DuckDB ベースのファクター計算を目指す設計が含まれるが、一部実装（ファイル末尾の calc_momentum の続き）が未完成または切り出し途中の箇所が見られます。今後の拡張で完了予定です。

---

## [0.1.0] - 2026-04-23

初期リリース。以下の主要機能を含む最小可動セット。

### Added
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"

- コア機能
  - 環境設定管理（kab usys.config）
  - ログ設定ユーティリティ（kab usys.utils.logging_setup）
  - プロセス優先度ユーティリティ（kab usys.utils.process_priority）
  - ポートフォリオ構築ライブラリ（kab usys.portfolio.*）
  - Execution サブシステム起動スクリプト（run_execution.py）
  - Monitoring サブシステム起動スクリプト（run_monitoring.py）
  - 設定ウィザード CLI（kab usys.config_setup）
  - 設定検証 CLI（kab usys.validate_config）
  - Paper Trading 検証レポートツール（kab usys.tools.paper_verification_report）
  - DuckDB / SQLite を用いたデータ連携基盤（設定でパス指定可能）

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

---

注記:
- 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、実際の git 履歴やリリース日付・担当者情報を元に追記・修正できます。