# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
バージョン情報はパッケージの __version__（0.1.0）に基づきます。

## [0.1.0] - 2026-04-17

### Added
- 起動スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine を起動・監視するエントリポイントを追加。ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、およびスレッドでのエンジン実行と停止フラグ処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプトを追加。外部停止フラグファイルを監視して安全にループを終了する仕組みを実装。

- 環境設定関連 CLI を追加
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成・更新する機能を追加。シークレット項目のマスク表示、選択肢、デフォルト値、保存確認などを提供。
  - validate_config.py: 起動前に .env と config/*.yaml の設定整合性をチェックする CLI を追加。--strict オプションで警告を FAIL 扱いにすることが可能。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（.env と .env.local の読み込み、OS 環境変数の保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化にも対応。
  - .env のパーシングを改良（export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート）。
  - Settings クラスを追加し、各種環境変数（J-Quants / kabu API / DB パス / モニタ閾値 / PAPER_TRADING 関連等）をプロパティで提供。PAPER_FILL_MODE のバリデーションや paper_sqlite_path、kill_flag_clear_on_start 等の設定を公開。

- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder: シグナルの選別（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコアが全てゼロの場合は等分配へフォールバック。
  - risk_adjustment: セクター集中制限を実施する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（既知レジームに対するマッピングと未知レジーム時の警告フォールバックを実装）。
  - position_sizing: 各銘柄の発注数を算出する calc_position_sizes を追加。allocation_method（"risk_based" / "equal" / "score"）対応、単元株丸め、max_position_pct / max_utilization による上限、aggregate cap によるスケーリングと残余配分ロジック、cost_buffer 考慮を実装。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows と POSIX(Linux/macOS/FreeBSD) を吸収し、権限不足や未対応 OS は警告でスキップ。

- モニタリング・レポート
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率、成功率、送信率、レイテンシ等を集計し P95 等を算出。閾値に基づく PASS/FAIL を判定。CLI 引数 --from/--to/--db をサポート。

- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを保証（冪等に実行可能）。

### Changed
- run_monitoring:
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能に（デフォルト 60 秒）。不正な値（0 以下や非整数）は警告を出してデフォルトにフォールバックする挙動を追加。
  - 監視は実行環境にかかわらず本番用 sqlite_path を使用する挙動（Monitoring は本番 DB を参照する前提）を明示。
  - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。

- run_execution:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
  - RiskManager のデフォルト設定を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連、max_drawdown 等）。initial_portfolio_value を broker.get_available_cash() で初期化するよう変更。
  - ExecutionEngine をスレッドで実行し、停止フラグを監視して安全停止を行うフローに変更（PID ファイル取り扱い、停止フラグ検知の早期退出など）。

- config/Settings:
  - KABUSYS_ENV と LOG_LEVEL の有効値チェックを強化。無効値は ValueError を送出するため、起動前に validate_config を使うことを推奨。
  - データベース・監視に関する設定（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種閾値等）をプロパティとして整理。

- ロギング / エラーハンドリング:
  - run_monitoring の check_once 呼び出しで例外を捕捉してログ出力し、次のポーリングを継続する堅牢化を追加。
  - process_priority や CPU affinity の失敗時は警告ログでスキップするように変更（起動失敗を避ける）。

### Fixed
- .env パーサの不具合回避・堅牢化
  - export プレフィックスやクォートされた値のバックスラッシュエスケープ、インラインコメントの判定などを正しく処理するよう改善。これにより .env の複雑な記述でも想定どおり環境変数がロードされるようになった。

- DB パス存在チェックのユーザー向け情報改善
  - validate_config にて DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合に警告を出す（起動時に自動作成される可能性があることを注記）。

### Documentation / Developer experience
- config_setup が生成する .env ファイルのテンプレートを整備（コメント付き、Git にコミットしない旨の注意書き）。
- validate_config が PyYAML の有無を判定して YAML 検証の可否をユーザーに通知。
- パッケージのメタ情報（kabusys.__version__ = "0.1.0"）を設定。

### Internal / Notes
- DuckDB 接続を分析（ファクター計算 / momentum 等）や ExecutionEngine のロギング / 分析用に幅広く導入。
- Portfolio・Signal・Risk 周りは純粋関数ベースで副作用を持たない設計（メモリ内計算）を意識して実装。
- 一部の TODO コメント（例: price のフォールバック、銘柄別 lot_size 対応など）を残し、将来の拡張ポイントを明示。

---

このリリースは初期機能群の整備を目的としています。実運用にあたっては .env の設定（特に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）と validate_config による検証を必ず実施してください。問題や追加要望があれば issue を作成してください。