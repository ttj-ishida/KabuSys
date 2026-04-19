CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。  
日付はコミット / リリース時点の目安です。

0.1.0 - 2026-04-19
-----------------

Added
- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用する設計（MockBrokerClient の利用を想定）。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) を扱う制御を実装。
    - ExecutionEngine の起動前に monitoring 用テーブルの存在を保証する init_monitoring_db 呼び出しを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（意図的な分離）。
    - 停止フラグ (data/stop_requested.flag) による安全停止をサポート。
- 設定管理とウィザード
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート判定を .git または pyproject.toml で行う）。
    - .env / .env.local の読み込み順と保護キー（OS 環境変数を上書きしない挙動）を実装。
    - .env 行の詳細なパーサ実装（export プレフィックス、クォート文字のエスケープ、インラインコメントの扱い等）。
    - Settings クラスを実装し、各種環境変数への安全なアクセス（必須のチェック、デフォルト値、バリデーション）を提供。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加（シークレットマスク、選択肢、デフォルト利用、確認・保存機能）。
- 設定検証 CLI
  - validate_config.py
    - .env および config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証まで実行。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定未設定や Kill Switch 設定等の警告）。
- 運用・診断ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（期間指定可、DB パスは環境変数または --db で指定可能）。
    - 稼働率、注文成功率、送信率、レイテンシ（AVG/Max/P95）などを集計し、閾値に基づく PASS/FAIL を判定。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合のフォールバック挙動を定義（等配分 + WARN）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear の基本マップ、未知レジームは WARN と 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ想定）の考慮を実装。
    - スケールダウン後の残余キャッシュによる端数分配を行うアルゴリズムを実装。
- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout 出力のみで継続。
    - デフォルトLOG_DIR、LOG_LEVEL の解決順を明確化。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。
    - Windows／POSIX の差異を吸収。失敗時は警告を出して安全にスキップ。
- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* から呼び出し、監視テーブルの存在を保証（冪等）。
- パッケージ初期化
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- ログ出力の標準化: StreamHandler を stderr ではなく stdout に統一（cron / Task Scheduler からの起動で stdout/stderr を一本化する運用を考慮）。
- .env 読み込みの振る舞いを明示化:
  - OS 環境変数は保護され、.env.local は .env より優先して読み込み（ただし OS 環境変数が優先）。
- 実行スクリプトのプロセス優先度設定を起動直後に行うように変更（パフォーマンス優先度が必要な処理の早期確保）。

Fixed
- .env パースの堅牢化:
  - export プレフィックス、シングル/ダブルクォートの内部エスケープ、インラインコメント（クォートなしの場合は空白直前の # をコメントとみなす）等を正しく扱うよう改善。
- .env 書き込みテンプレートの追加（config_setup が生成する .env の整形）。

Deprecated
- なし（初期リリース）。

Removed
- なし（初期リリース）。

Security
- なし（初期リリース。ただしシークレット値は .env に保管する前提。.env を Git にコミットしない旨の注意喚起を config_setup に含む）。

Known issues / Notes
- research/factor_research.py の calc_momentum 関数が途中で終わっており（ファイル末尾で未完の実装を確認）、完全実装は今後の作業となります。現状ではリサーチ周りはスケルトン／下書きが含まれます。
- position_sizing のコメントにある通り、銘柄別 lot_size の拡張や価格欠損時のフォールバック（前日終値など）は将来的な改善対象です。
- ログディレクトリ作成やプロセス優先度／CPU affinity の設定は環境により失敗する可能性があり、その場合は警告を出して処理を継続する設計になっています（運用側で適切な権限を付与することを推奨します）。
- Monitoring は明示的に本番 sqlite_path を使う設計のため、意図せず本番 DB を参照してしまわないよう環境変数の設定には注意してください。

運用メモ
- 停止制御:
  - run_monitoring / run_execution はプロジェクトルート下 data/stop_requested.flag の存在で安全に停止します。外部から停止したい場合はこのフラグファイルを作成してください。
- データベース:
  - デフォルト DuckDB, SQLite のパスは .env の DUCKDB_PATH / SQLITE_PATH（または PAPER_TRADING_SQLITE_PATH）で上書き可能です。
- 設定チェック:
  - デプロイ前に python -m kabusys.validate_config を実行して設定の不備を検出してください。
- .env 作成:
  - 初期設定は python -m kabusys.config_setup で対話的に作成できます。

-----------------------------------------------------------------------------