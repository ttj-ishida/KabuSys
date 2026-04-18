CHANGELOG
=========

すべての重要な変更は Keep a Changelog の規約に従って記載しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
  - 停止制御: 起動スクリプトはプロジェクト直下の data/stop_requested.flag を監視し、フラグで安全停止できる仕組みを提供。Execution は実行用 PID ファイル(data/execution.pid) を利用。
- 設定管理
  - config.py: プロジェクトルート（.git または pyproject.toml）に基づく自動 .env ロード機能を実装。export プレフィックス・クォート付き値・エスケープ・インラインコメントのパースに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを追加し、環境変数から型付き設定を取得。各種プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）にバリデーションとデフォルトを実装。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の環境変数をサポート。
- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。テンプレート・説明を含む項目定義を提供。
  - validate_config.py: .env と config/*.yaml を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML があれば）等を実行。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（pure function）
  - portfolio/portfolio_builder.py: シグナルの候補選定および等金額・スコア加重配分の計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジック（calc_position_sizes）を実装。allocation_method（"risk_based" / "equal" / "score"）に対応、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash によるスケーリング）などをサポート。
  - portfolio/__init__.py: 上記関数をエクスポート。
- 運用ユーティリティ
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_DIR/LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定と CPU affinity 設定を追加。set_process_priority("high" 等) と set_cpu_affinity(N) を提供。権限不足・非対応 OS 時は警告ログでスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成立率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定（しきい値はソース内で定義）を出力。--from/--to/--db オプションに対応。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db 呼び出しを run_monitoring/run_execution で行い、監視テーブルの存在を保証（冪等）。
- DuckDB / SQLite
  - duckdb 接続を各起動処理で確立（分析用 DuckDB と運用用 SQLite を明確に分離）。

Changed
- ロギング設計: 起動スクリプト群から共通の setup_logging を使うよう統一。ファイルローテーションと stdout 統合により運用ログの一貫性を向上。
- 環境変数ロード順序: OS 環境変数 > .env.local > .env の順でロードするよう明確化。既存の OS 環境変数は protected として .env を上書きしない。
- run_monitoring の挙動: 監視プロセスは常に settings.sqlite_path（本番用 sqlite_path）を使用する設計に変更（本番監視データは環境にかかわらず一元化）。

Fixed
- 環境ファイルパースの堅牢化: export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどで誤解析しないよう改善。
- position_sizing の合計投資金額が available_cash を超えた場合のスケーリングロジックを実装（小数切捨て後の残差分を lot 単位で再配分するアルゴリズムを導入）。

Deprecated
- なし

Removed
- なし

Security
- 機密値（J-Quants トークンや kabu API パスワード）は .env にて保管し、config_setup の出力ではマスクして表示。Git に .env をコミットしない旨を README/テンプレートに明記。

Notes / Migration
- 実行方法
  - 監視: python -m kabusys.run_monitoring を直接実行して監視ループを起動できます（モジュールをエントリとして実行する場合はパッケージ構成に合わせて起動してください）。
  - 実行エンジン: python -m kabusys.run_execution により ExecutionEngine を起動。paper_trading モードでは paper_trading 用 DB を使用するため本番 DB とは分離されます。
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - 検証レポート: python -m kabusys.tools.paper_verification_report
- 重要な環境変数（本リリースで導入/利用している主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: 開発・ペーパー・本番を指定（development / paper_trading / live）。設定ミスは validate_config で検出される。
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60 秒。
  - PAPER_FILL_MODE: paper_trading の MockBrokerClient の填埋モード（instant / partial / never / reject）。無効値は例外。
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）。
  - DUCKDB_PATH / SQLITE_PATH: 各 DB のパス（デフォルトあり）。
  - KILL_FLAG_CLEAR_ON_START: 本番での自動 Kill フラグクリアを禁止するための安全設定（デフォルト 0）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用途など）。
  - LOG_DIR / LOG_LEVEL: ログ出力先・レベル。
- DB マイグレーション
  - monitoring 用テーブルは起動時に init_monitoring_db() を呼んで冪等に作成されます。既存 DB を置き換える必要は通常ありませんが、スキーマ変更がある場合は適切なマイグレーション手順を別途実行してください。
- 未実装 / 既知の制限
  - research/factor_research.py はファイル末尾が途中で切れており実装が完了していない部分があります（モメンタム計算関数の実装途中）。本格運用前に該当モジュールの完成が必要です。
  - position_sizing の price フォールバックは TODO コメントあり（price が欠損した場合に前日終値や取得原価を使う拡張が未実装）。
  - 一部の機能は権限（プロセス優先度設定や CPU affinity）や OS の実装差に依存するため、権限不足時はログ警告を出してスキップします。
- API/戻り値の注意
  - portfolio モジュールの関数は純粋関数として設計され、データベースにはアクセスしません。戻り値のフォーマットはドキュメントや関数 docstring に従ってください（例: calc_position_sizes は {code: shares} を返す）。

作者
- KabuSys 開発チーム

--- 

（注）本 CHANGELOG は提供されたソースコードの静的解析に基づく推測により作成しています。実際のコミット履歴やリリースノートと完全に一致しない場合があります。必要であれば、より正確な差分（git のコミットログ）を元にした CHANGELOG 生成を支援します。