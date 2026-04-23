Keep a Changelog
=================
すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
-------------

[0.1.0] - 2026-04-23
--------------------

Added
- 基本機能の初期実装（初回公開リリース: 0.1.0）。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による優雅な停止処理をサポート。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する旨を明示。
    - SQLite / DuckDB への接続初期化、例外発生時のログ出力を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。スレッドで engine.run_session を実行し停止フラグで停止。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用（data/paper_trading.db がデフォルト）により本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる。
    - 実行 PID を data/execution.pid に記録する仕組み（pid_file 引数）。
- 設定管理:
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順序を実装（OS 環境変数が優先され、.env.local は上書き可能）。
    - 複雑な .env 行パーサ実装（export プレフィックス、クォート・エスケープ、インラインコメント処理など）。
    - Settings クラスに各種設定プロパティを提供（DB パス、API トークン、Paper Trading 設定、監視閾値、環境判定等）。
    - PAPER_FILL_MODE の検証・制約を実装（instant/partial/never/reject）。
- 設定支援・検証ツール:
  - config_setup.py
    - .env を対話的に作成・更新するウィザードを実装。既存 .env の読み込み、シークレット値のマスク表示、確認後の保存をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル検証、DB パスの親ディレクトリ確認、YAML パース検査（PyYAML がある場合）などを実行。
    - --strict オプションで警告も失敗扱いにできる。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイル（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する関数を追加。Windows と POSIX の差分を吸収。
    - CPU affinity を設定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出してフォールバックする。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等重みにフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - 未知のレジームは警告を出して 1.0 にフォールバック。
    - 注: unknown セクターはセクター上限の対象外として扱う実装。
  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装（risk_based / equal / score の allocation_method サポート）。
    - lot_size（単元）単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap とスケーリング処理を実装。
    - コスト保守見積のため cost_buffer を加味し、残差処理で追加配分するアルゴリズムを備える。
    - 将来拡張用の TODO コメント（銘柄毎の lot_size を持たせる等）を記載。
- レポート・分析ツール:
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを実装。期間指定可能（--from / --to）および DB パス指定（--db）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - PASS/FAIL 基準（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。
- リサーチ基盤（部分実装）:
  - research/factor_research.py
    - モメンタム / バリュー / ボラティリティ / 流動性ファクター計算方針と一部定数、calc_momentum のインターフェースを追加（DuckDB を用いた計算を想定）。※ファイル末尾は実装途中の状態（トランケートあり）。
- パッケージメタ:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため新規追加が中心）。

Fixed
- なし（新規機能実装）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known issues / TODO
- run_monitoring の挙動:
  - 監視プロセスは「監視 DB（sqlite_path）は環境にかかわらず本番用 path を使用する」設計になっています。開発・テスト時に誤って本番 DB に書き込みたくない場合は設定に注意してください。
- .env 自動読み込み:
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- factor_research.py は現状実装が途中（ファイル末尾で途中切れ）。本格運用前に完全実装とテストが必要です。
- risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少計算される可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- position_sizing:
  - 銘柄毎の単元（lot_size）を将来サポートするための拡張 TODO を残しています。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続する安全設計。ただしその旨が stderr に出力されます。
- process_priority / set_cpu_affinity:
  - 権限が不足する環境や未対応プラットフォームでは設定に失敗して警告を出し、処理をスキップします。
- テスト・型情報:
  - 一部ファイルに type ignores や # noqa 指示が含まれます。外部依存（psutil, duckdb, PyYAML 等）は実行環境にインストールされている必要があります。

参考: 主要 CLI
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もし CHANGELOG に追記してほしい点（例えば公開日を別にする、カテゴリ分けを変更する、より詳細な変更ログをファイル単位で追加する等）があれば教えてください。