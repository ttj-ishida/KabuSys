CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。  
注: 以下は提示されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------
- なし（初期リリースの記録は下の 0.1.0 を参照）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本リリース: KabuSys 自動売買システムの初期実装を追加。
- 設定管理
  - 環境変数/`.env` 自動読み込み機能を追加（プロジェクトルート探索: .git または pyproject.toml）。
  - 高度な .env パーサを実装: export 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で扱えるようにした。
  - 設定時のバリデーション機能を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の許容値チェック）。
- 設定支援/検証 CLI
  - config_setup: 対話式ウィザードで `.env` を初期作成・更新可能に。
  - validate_config: .env と config/*.yaml の存在・基本妥当性を検査する CLI。--strict モードで警告を FAIL 扱いにできる。
  - validate_config は PyYAML 未インストール時に YAML の内容検証をスキップして警告を出す。
- 実行/監視用エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組立て、ExecutionEngine のセッション起動と停止フラグ処理を実装。KABUSYS_ENV=paper_trading 時は専用（分離された）SQLite DB を使用。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出や例外ハンドリングを備える。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
  - 停止フラグ/PID 管理: data 内の stop_requested.flag、execution.pid 等に対応。
- データベース / 分析
  - DuckDB サポートを追加（duckdb 接続オブジェクトを引き回す設計）。
  - 監視用 SQLite 初期化ヘルパ（init_monitoring_db）を組み込み、冪等にテーブルを保証。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定 (select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) を実装。スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限 apply_sector_cap、および市場レジームに基づく乗数 calc_regime_multiplier を実装（regime: bull/neutral/bear）。
  - position_sizing: 各銘柄の発注株数決定ロジック calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）、単元株丸め(lot_size)、max_position_pct/max_utilization による上限、aggregate cap によるスケールダウン、残差処理によるロット追加配分を行う。
  - 設計によりこれらは DB を参照しない純粋関数で、ユニットテストしやすい。
- 研究モジュール
  - research/factor_research: DuckDB を使ったファクター計算機能（モメンタム、移動平均乖離、ATR、出来高/売買代金指標等）。prices_daily / raw_financials テーブルを想定した実装。
- ユーティリティ
  - utils/process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を実装。PSUtil の制約やアクセス権限エラーに対してフォールバックして警告を出す。set_cpu_affinity による CPU ピンニングも提供。
- ツール
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95レイテンシ等を集計して PASS/FAIL 判定を出力。期間フィルタや DB パス指定 (--from/--to/--db) に対応。
- ドキュメント化・メタ
  - パッケージ __version__ を "0.1.0" に設定。
  - 各モジュールに豊富な docstring と実装上の注意（TODO / 注意事項）を追加。

Changed
- 初期リリースのため該当なし（以降のリリースで変更履歴を追加予定）。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- .env ファイルは絶対にリポジトリにコミットしない旨を config_setup の生成ヘッダに明示。

Notes / 実装上の注意（既知の制約・TODO）
- apply_sector_cap: price_map の欠損（price == 0.0）時にエクスポージャーが過少見積りされる可能性がある旨の注記（将来的に前日終値等のフォールバックを検討）。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）。将来的には銘柄ごとの lot_size を持たせる拡張を予定。
- validate_config: PyYAML が無い場合は YAML 構文チェックをスキップして警告を出す。
- run_monitoring: 監視は常に settings.sqlite_path（本番）を参照する設計になっているため、paper_trading 環境での監視 DB 分離が必要な場合は運用上の注意が必要。
- process_priority / set_cpu_affinity: 実行環境の権限 (nice 値変更や CPU affinity の設定権限) に依存し、失敗時は警告を出してスキップする。
- research/factor_research: DuckDB の prices_daily / raw_financials のスキーマに依存。十分な履歴データがない場合は None を返す設計。

Configuration (主な環境変数・デフォルト)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- LOG_LEVEL (default: INFO)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START (default: 0)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化

今後の予定（例）
- per-stock lot_size のサポート（マスタ参照）
- price 欠損時のフォールバックロジック（apply_sector_cap の改善）
- 研究モジュールの追加ファクター・最適化・テスト強化
- モジュール間の統合テスト、CI の整備

[0.1.0]: https://example.org/releases/0.1.0 (initial release)

以上。必要であれば、リリースノートの粒度（より詳細なコミット単位の変更点、あるいは運用手順・マイグレーション手順）を増やして調整します。