CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- (なし)

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開しました。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB (data/paper_trading.db) を利用して本番 DB と分離します。エンジンは別スレッドで実行・停止フラグ監視を行います。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用します。停止はプロジェクト直下の data/stop_requested.flag によるフラグで行います。
- 設定関連
  - config.Settings: 環境変数ベースの設定管理クラスを追加。多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。OS 環境変数は保護され、.env.local は上書き可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱いなど多数のケースに対応する堅牢なパーサを実装。
  - 設定ウィザード: config_setup に対話式 wizard を追加し .env の初期作成・更新を支援。秘密値はマスク表示、デフォルトや選択肢をサポート。
  - 設定検証 CLI: validate_config を追加。必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在とパース検証、--strict モードで警告を FAIL 扱いにできます。
- データベース / 分析
  - DuckDB / SQLite 接続サポートを追加。duckdb_path / sqlite_path / paper_sqlite_path の設定および初期化ユーティリティを組み込み（監視テーブルの冪等初期化など）。
- ロギング / プロセス管理
  - utils.logging_setup.setup_logging を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ自動作成、ログレベル解決順（引数 > 環境変数 > デフォルト）。
  - utils.process_priority: プロセス優先度設定ユーティリティを追加。Windows / POSIX の差分を吸収して high/normal/low を設定。CPU affinity を設定する set_cpu_affinity も提供。
  - 起動スクリプトは開始時にプロセス優先度を "high" に設定。
- ポートフォリオ構築
  - portfolio.portfolio_builder: シグナル選定（select_candidates）と配分計算（calc_equal_weights, calc_score_weights）を実装。スコア全0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。unknown セクターの扱いやレジーム別の乗数を定義。
  - portfolio.position_sizing: position sizing 実装。allocation_method（risk_based / equal / score）をサポートし、lot_size、cost_buffer、max_position_pct、max_utilization、aggregate cap によるスケーリングを実装。スケールダウン時の端数配分アルゴリズムを備える。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を出力。閾値はファイル内定数で定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。期間フィルタをサポート（--from / --to / --db）。
- 研究 / ファクター計算（初期）
  - research.factor_research: ファクター計算モジュールの骨子を追加。DuckDB 接続を受け取る設計、モメンタム / MA200 / ATR / ボリューム等の計算を想定（モジュールは一部実装中）。

Changed
- ロギング出力先はコンソールで stderr ではなく stdout を使用するように方針を明示（cron / scheduler のリダイレクト運用を考慮）。

Fixed
- MONITOR_POLL_INTERVAL のパースを堅牢化: 無効な値や 0 以下の値を指定した場合に警告を出してデフォルト（60 秒）にフォールバックするようにしました（run_monitoring）。
- calc_score_weights: 全銘柄のスコアが 0 の場合に等金額配分へフォールバックし、警告ログを出すよう改善。
- .env 読み込み時の例外ハンドリングを改善し、ファイル読み込み失敗時に警告を出して処理を継続します（config._load_env_file）。

Security
- (なし)

Deprecated
- (なし)

Removed
- (なし)

Notes / Implementation details
- 停止制御はプロジェクト内 data/stop_requested.flag を用いる運用を想定（run_execution/run_monitoring）。ExecutionEngine は起動時に既に停止フラグが立っている場合は起動をスキップします。
- run_monitoring は監視用 DB テーブルを初期化するため sqlite3 コネクションを開き、duckdb も接続します。例外発生時は例外ログを出し次のポーリングへ継続します。
- Settings.env の値検証により、無効な KABUSYS_ENV / LOG_LEVEL 指定時には ValueError を発生させ起動前に問題を明示します。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続します。

今後の予定（例）
- research.factor_research の完全実装（ファクタ群の SQL / 集計ロジックの完成）。
- ExecutionEngine / BrokerClient の詳細な実装および単体テストの追加。
- 単体テストと CI 構成の追加、ドキュメントの拡充（PortfolioConstruction.md 等の参照ドキュメントの整備）。

---