# CHANGELOG

すべての重要な変更は Keep a Changelog の原則に従って記載しています。  
バージョンと変更内容は、リポジトリ内のコードから推測して作成しています。

## [Unreleased]

### Added
- 監視・実行用の起動スクリプトを追加・整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止制御に data/stop_requested.flag を利用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離する。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数を保護）および多数の Settings プロパティを実装（J-Quants / kabu API / DB パス / 監視閾値など）。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml の設定チェック CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio/portfolio_builder.py: シグナルの選定（スコア順）および等配分/スコア配分重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用関数と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積りをサポート。
- ユーティリティを追加
  - utils/logging_setup.py: すべての起動スクリプトから利用可能な統一ログ設定を実装（stdout StreamHandler + 日次ローテート FileHandler、LOG_DIR/LOG_LEVEL 経由で設定可能）。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定（Windows/Linux/Mac の差分吸収）および CPU affinity 設定ユーティリティを実装。
- 検証・レポートツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み、稼働率、注文成功率、送信率、レイテンシ（P95 を含む）などを集計して PASS/FAIL 形式で出力するツールを追加。閾値はソース内に定義（稼働率 99% など）。

### Changed
- 起動スクリプトの初期化順序と安全性向上
  - すべての起動スクリプトで最初に set_process_priority("high") を呼び出し、重要プロセスの優先度を上げるようにした。
  - run_execution.py は起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に停止フラグがある場合は起動をスキップするよう変更。
  - run_monitoring.py は監視 DB の初期化（init_monitoring_db）を呼ぶことで監視テーブルの存在を保証（冪等）。
- 設定ロードの振る舞いを明確化
  - config.py の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うようにし、CWD に依存しない動作に変更。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ（_parse_env_line）は export プレフィックス、クォート、バックスラッシュエスケープ、コメントルールをサポートして堅牢化。
  - _load_env_file は override と protected 引数を導入し、OS 環境変数を上書きしない安全な読み込みを行う。
- ログ設定のデフォルトとフォールバックの扱いを整理
  - setup_logging はログディレクトリ作成に失敗した場合にファイルハンドラをスキップして標準出力のみで動作するようフォールバック実装。
- ポートフォリオ計算ロジックの挙動整理
  - calc_score_weights: 全スコアが 0.0 の場合に等金額にフォールバックし、警告ログを出すようにした。
  - apply_sector_cap: "unknown" セクターの扱い（上限適用除外）を明示。
  - calc_position_sizes: risk_based / equal/score 両者で lot_size 単位の丸め、per-position 上限、aggregate cap のスケーリングを実装。価格欠損時のログ出力とスキップ動作を明確化。

### Fixed
- 環境変数の不正値・境界値に対する堅牢性向上
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数を検出した場合にデフォルトにフォールバックし警告を出力（run_monitoring.py）。
  - Settings.paper_fill_mode で無効な値を検出して ValueError を送出するようにした（許可値の明示化）。
  - Settings.env / log_level の検証を実装し、不正値で ValueError を投げることで早期に不整合を検出。
- 起動時リソースクリーンアップ
  - run_monitoring/run_execution の finally ブロックで SQLite/duckdb 接続を確実にクローズするようにした。

### Documentation / Misc
- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 開発者向けメモや TODO をソースに残し、将来的な拡張ポイント（銘柄別 lot_size、価格フォールバックなど）を明示。

## [0.1.0] - 2026-04-18

初回公開想定のまとめリリース。上記の機能群（起動スクリプト、設定管理、設定ウィザード、検証ツール、ポートフォリオ構築ユーティリティ、実行エンジン周辺ロジック、ログ/プロセスユーティリティ、Paper Trading 検証レポート）が導入されました。

- 主要機能
  - 自動売買実行エンジン（ExecutionEngine）の起動スクリプトと依存コンポーネント組立て（OrderManager, RiskManager, Reconciler, OrderRepository 等）。
  - SystemMonitor 用のポーリング監視ループ（monitoring）。
  - ペーパートレードと本番を分離する DB 設定と MockBroker の切替。
  - 環境設定ウィザード (.env) と起動前設定検証ツール。
  - DuckDB / SQLite を利用したデータ処理基盤（分析・検証ツール向け）。
  - ポートフォリオ構築（候補選定・重み付け・ポジション決定）とリスク調整ロジック。
  - ロギングとプロセス優先度設定のユーティリティ群。
  - Paper Trading 向け検証レポート生成ツール。

- 品質・運用面
  - 起動時の安全弁（停止フラグ、PID ファイル参照、早期バリデーション）を導入。
  - 各種閾値や動作は環境変数で容易にカスタマイズ可能（例: KABUSYS_ENV, SQLITE_PATH, DUCKDB_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE 等）。

---

注: 本 CHANGELOG は提供されたソースコード内容に基づき推測して作成しています。実際のリリース履歴や日付はリポジトリ運用方針に合わせて調整してください。