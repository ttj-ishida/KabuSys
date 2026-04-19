CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------
### Added
- MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔の上書き（不正値はデフォルトにフォールバック）。
- run_monitoring/run_execution 起動スクリプトにおける停止フラグ（data/stop_requested.flag）検出ロジック。
- 起動時にプロセス優先度を設定するユーティリティ（utils.process_priority）を導入し、起動スクリプトで High 優先度を設定するようにした。
- ログ設定ユーティリティ（utils.logging_setup）で stdout ストリームハンドラと日次ローテートのファイルハンドラを統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフェールセーフを追加。

### Changed
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番パス）を使う設計になった旨を明確化。
- 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録して本番 DB と分離する動作を実装。
- 起動スクリプト側で PID ファイルパスや停止フラグの取り扱いを統一（Settings で PID/KILL フラグパスを管理）。

### Fixed
- .env ファイルの読み込み処理（config._load_env_file / _parse_env_line）で export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどを堅牢化。
- 環境変数の自動ロードは OS 環境変数を保護する仕組み（protected set）を導入して .env.local の上書きを適切に制御。

0.1.0 - 2026-04-19
-----------------
初期リリース。主な機能・モジュールを追加。

### Added
- 基本設定 / 環境管理
  - kabusys.config: .env 自動読み込み（.env / .env.local の優先順）、必須環境変数検査ユーティリティ（Settings クラス）。
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI（KABUSYS_ENV、API トークン、DB パス等の設定項目を案内）。
  - validate_config: 起動前に環境変数と config/*.yaml を検証する CLI（--strict オプション対応、PyYAML 未インストール時のフォールバック）。

- 起動スクリプト / 実行制御
  - run_execution: ExecutionEngine を組み立てて別スレッドで実行。BrokerFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、停止フラグ検出での安全停止処理、paper_trading 時の DB 分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。監視 DB 初期化、duckdb 接続、停止フラグ検出、例外発生時の例外ログ→ループ継続。

- 監視 / DB 初期化
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）を実行スクリプトで行い、監視テーブルの存在を保障。

- ユーティリティ
  - utils.logging_setup: ルートロガーの初期化関数。StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）を設定。既存ハンドラのクリーンアップ処理を行う。
  - utils.process_priority: psutil を利用したプラットフォーム対応のプロセス優先度設定（Windows/Linux/macOS 等を吸収）。CPU affinity 設定関数も追加。権限不足時は警告を出し安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合等金額へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を計算。未知レジームはログ警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じた発注株数計算。単元株丸め（lot_size）、1銘柄上限(max_position_pct)、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、端数処理ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計して検証レポートを出力。指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等。閾値比較により PASS/FAIL を判定。P95 計算・日付フィルタ対応。

- リサーチ / ファクター計算（作業中）
  - research.factor_research: DuckDB を使用したファクター計算モジュールを追加（モメンタム/MA/ATR 等の計画・定数定義を含む）。（計算関数群の実装は継続中）

### Changed
- パッケージメタ情報: kabusys.__version__ を 0.1.0 として設定。

### Fixed
- 起動スクリプト・DB 接続周りのリソース確実解放（finally ブロックで sqlite/duckdb 接続を閉じる処理を追加）。
- run_execution: 停止フラグ検出時のスレッド停止手順を安全化（engine.stop() 呼び出し、join のタイムアウトを設定）。

### Documentation
- 各モジュールに docstring と使用例を追加し、動作意図・引数・戻り値・例外条件を明示。

Deprecated / Removed / Security
-------------------------------
- なし（初期リリースにつき該当なし）。

注意
----
- 本 CHANGELOG はコードベースから推測して作成したもので、実際のリリースノートと差分がある場合があります。必要に応じて日時・バージョン・詳細を調整してください。