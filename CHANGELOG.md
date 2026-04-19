# Changelog

すべての変更点は「Keep a Changelog」準拠で記載しています。セマンティックバージョニングに従います。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、BrokerClientFactory 経由のブローカ初期化、OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）をサポート。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）に分離して実行。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する挙動になっている。
- 設定管理
  - config.py: .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）を実装。細かな .env パース（export プレフィックス、クォート／エスケープ、インラインコメント処理）に対応。Settings クラスを提供し、環境変数の取得と妥当性検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）を行う。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目のマスク表示、デフォルト値・選択肢、.env の書き出しテンプレートを提供。
  - validate_config.py: 起動前の設定検証用 CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境用の追加注意（LINE 設定、KILL_FLAG_CLEAR_ON_START）などを実施。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク用 signal_rank）と等配分・スコア加重配分の実装（calc_equal_weights, calc_score_weights, select_candidates）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックや debug ログを出力。
  - portfolio/position_sizing.py: ポジションサイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下合計の aggregate cap とスケーリング、cost_buffer による保守的見積もり、残余キャッシュを用いた端数処理を行う。
  - portfolio/__init__.py により主要関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。既存ハンドラのクリア処理、ログディレクトリ自動作成、環境変数 LOG_LEVEL / LOG_DIR の優先度に対応。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。Windows / POSIX を吸収し、psutil を用いて nice 値／Windows 優先度クラスを設定。CPU affinity 設定関数も提供。権限がない場合には警告を出して安全にスキップ。
- ツール類
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを読み、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定する。デフォルト基準値（稼働率 99%、成立率 90% 等）を定義。
  - tools パッケージ初期化ファイルを追加。
- 研究用モジュール（骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加。モメンタム・MA200 乖離・ATR 等の定数と calc_momentum 関数の設計方針を記載（prices_daily / raw_financials テーブル参照）。（実装途中のファイルを含む）
- パッケージ初期化
  - __init__.py にバージョン番号 __version__ = "0.1.0" を設定。

### Changed
- n/a（初回リリースのため既存コードの変更はなし）

### Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

### Notes / 補足
- .env 自動読み込みはデフォルトで有効。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB として常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）で DB を分離します。
- process priority / CPU affinity の設定は OS 権限に依存します。権限不足時は警告を出しスキップします。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続します。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター計算 SQL/Python 実装）
- ExecutionEngine / SystemMonitor のユニットテスト追加
- DuckDB スキーマ記述、config/*.yaml のデフォルト生成スクリプトの整備

もし CHANGELOG に追記して欲しい点（特定のファイルや挙動の詳細、より技術的な説明など）があれば教えてください。