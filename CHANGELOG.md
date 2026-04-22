CHANGELOG
=========

すべての項目は Keep a Changelog のフォーマットに従っています。コードベース（src/kabusys）から推測できる変更点・導入機能を日本語でまとめています。

Unreleased
----------

### Added
- 環境設定関連の改善とユーティリティ
  - .env ファイルの自動読み込み実装（プロジェクトルートを .git / pyproject.toml で探索）。OS 環境変数は保護され、.env.local は .env を上書き可能。
  - .env パーサを強化（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
  - Settings クラスに多数の設定プロパティを追加（J-Quants / kabu API / LINE / DB パス / PID / Kill flag オプション / 閾値等）。PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH のサポート。

- 起動スクリプト
  - run_execution.py を追加：ExecutionEngine の起動ロジックを実装。paper_trading 環境では専用の MockBrokerClient と data/paper_trading.db を使用（本番 DB と分離）。
  - run_monitoring.py を追加：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ file による停止検知を実装。

- 実行系コンポーネントの組み立て
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）等の連携コードを導入。RiskManager の初期設定（max_position_pct、max_utilization、rate_limit 等）を設定。
  - ExecutionEngine 起動時に PID ファイル管理、停止フラグ検出、デーモンスレッドでのセッション実行とグレースフルシャットダウンを実装。

- 監視・DB 周り
  - monitoring 用 DB 初期化を担う init_monitoring_db 呼び出しを起動時に実行（冪等に監視テーブルを確保）。
  - Monitoring は環境に関係なく production の sqlite_path を使用する設計（実運用の監視が別 DB で分離される意図）。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加：stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログレベル・ログディレクトリ解決順を実装し、ファイル作成不可時は標準出力のみで継続。
  - utils.process_priority.set_process_priority を追加：Windows/Linux/Mac の差分を吸収してプロセス優先度を設定。失敗時は警告でスキップ。
  - utils.process_priority.set_cpu_affinity を追加：プロセスの CPU affinity 固定機能を実装（利用可能なコアより大きい値が指定された場合の挙動も考慮）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等金額にフォールバックする警告あり。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の対象外にする動作を明示。
  - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、per-position / aggregate cap、コストバッファを用いたスケールダウン・残差分配アルゴリズムを実装。

- ツール類
  - kabusys.config_setup: 対話式ウィザードを追加し .env の初期作成・更新を支援。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、Kill flag など）をカバー。
  - kabusys.validate_config: 起動前検証 CLI を追加（--strict オプションで警告も FAIL 扱い）。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）内容パース検証。本番（live）向けの追加警告あり。
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出する。閾値（稼働率 99% など）を定義し PASS/FAIL を判定。

### Changed
- ログ出力の挙動：stderr ではなく stdout を StreamHandler で使用するように変更（cron / タスクスケジューラからのリダイレクトを想定）。
- Settings.env の妥当性チェックを強化し、許容値にない場合は ValueError を送出するようにした。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するフォールバック処理を追加。無効値の場合は警告を出してデフォルト（60 秒）を使用。

### Notes / TODO / WIP
- research.factor_research モジュールの実装は途中（ファイル終端付近で calc_momentum の途中で切れている）。引き続きモメンタム等のファクター計算を完成させる必要あり。
- position_sizing の価格欠損（price が 0.0 の場合）に関する TODO コメントあり。将来的に前日終値等を使ったフォールバックを検討する旨が記載されている。

[0.1.0] - 2026-04-22
--------------------

リリース初版（推定） — コードベースから推測される主な導入内容をまとめています。

### Added
- パッケージメタ情報
  - kabusys.__version__ を "0.1.0" に設定。

- 基本機能（Execution / Monitoring）
  - Execution Engine と監視（Monitoring）ワークフローを導入。起動スクリプト（run_execution.py, run_monitoring.py）を追加し、実行時のプロセス優先度設定、DB 接続（SQLite / DuckDB）、監視ループ／エンジン実行のライフサイクル管理を実装。
  - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用した運用制御を実装。

- Broker / Order / Risk / Reconciliation
  - BrokerClientFactory を介したブローカークライアント生成（paper_trading 環境では MockBrokerClient を使用）。
  - OrderRepository、OrderManager、Reconciler、RiskManager の導入。RiskManager は発注前に各種リスクルール（position 上限、利用率、サーキットブレーカ等）を適用。

- 監視 DB 初期化
  - init_monitoring_db を起動時に呼び出し、監視用テーブルを確保（monitoring 用テーブルが存在することを保証）。

- 設定管理・CLI
  - Settings クラスと settings グローバルインスタンスを導入し、環境変数ベースで各種設定を提供。
  - config_setup による .env 作成ウィザード。
  - validate_config による設定検証 CLI（--strict をサポート）。

- ロギング
  - 統一的なロギング設定ユーティリティ（setup_logging）を導入。日次ローテーション (30 日保持) のファイルハンドラとコンソール出力を設定。

- ユーティリティ
  - process_priority（優先度設定、CPU アフィニティ）ユーティリティを追加。
  - .env パーサと読み込みロジック（優先順位: OS 環境 > .env.local > .env）。

- Portfolio / Position sizing / Risk adjustment
  - 銘柄選定（select_candidates）、重み付け（等金額・スコア加重）、セクター上限制御（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）、ポジションサイズ計算（calc_position_sizes）を実装。単元株丸め、aggregate cap のスケーリング、残余配分アルゴリズムなどを含む。

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）を追加。稼働率・注文成功率・レイテンシ等を解析し PASS/FAIL 判定を出力。

### Changed
- 起動時の DB 接続方針
  - Monitoring は環境に関係なく production の sqlite_path を参照する設計にした点を明記（監視データは本番 DB を使用）。

### Fixed / Behavior
- .env の読み込みで既存の OS 環境変数を上書きしないよう保護（protected set）。.env.local は override=True で上書き可能。
- ログディレクトリ作成失敗時はファイルハンドラ生成をスキップし、コンソール出力のみで継続するフォールバックを実装。

### Known issues / Limitations
- factor_research.calc_momentum の実装が途中で終端している（ファイルが不完全）。ファクター計算モジュールはまだ未完成。
- 一部の TODO: 価格欠損時のフォールバックロジック、銘柄ごとの lot_size マスタ対応などの拡張予定。

Footer / Notes
---------------
- 上記 CHANGELOG はソースコードの実装内容・コメント・TODO などから推測して作成したものであり、実際のプロジェクト履歴（コミット単位の変更履歴）とは異なる場合があります。
- 追加の要求（例: 実際のコミットメッセージや特定のバージョン履歴を反映する等）があれば、その情報を提供してください。より実態に即した CHANGELOG を作成します。