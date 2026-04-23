CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースの目的や重大な設計意図は各項目の説明を参照してください。

[Unreleased]
------------

（現在未リリースの作業はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
  - 実行・監視スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、paper_trading 環境では専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用する。停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを含む。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用テーブルは常に本番 sqlite_path を利用する設計。
  - 設定・環境管理
    - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数優先）、環境変数パースロジック、Settings クラスを実装。多くの設定プロパティ（DB パス、Paper Trading 設定、監視閾値、環境種別など）を提供。
    - config_setup.py: .env を対話的に作成/更新するウィザード CLI を追加。
    - validate_config.py: .env と config/*.yaml の検証ツールを追加（--strict オプションで警告を失敗扱いにできる）。
  - ポートフォリオ構築（純関数）
    - portfolio/portfolio_builder.py: シグナル選定（上位 N 抽出）、等分配・スコア加重の重み計算を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap（現金上限でスケーリング）などを実装。cost_buffer 考慮による保守的見積りをサポート。将来的に銘柄別 lot_size 拡張を想定した TODO コメントあり。
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーに stdout StreamHandler と 日次ローテーションする TimedRotatingFileHandler を設定するユーティリティ。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を実装。権限不足等で失敗した場合は警告ログでスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（P95 など）を算出し PASS/FAIL 判定を出力。コマンドライン引数で期間や DB パスを指定可能。
  - 研究用モジュール（部分実装）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム等の設計と一部実装を含む）。（注：ファイルの末尾が未完了で一部実装が残る）

Changed
- 初期リリースのため、ライブラリ内の多数の設計・仕様を公表（Settings による統一設定取得、ログ周り・プロセス優先度の共通化など）。

Fixed
- N/A（初回実装）

Deprecated
- N/A

Removed
- N/A

Security
- 環境ファイル .env の扱いに関する注意を明記（config_setup にて .env を絶対にコミットしない旨を出力）。

Notes / Implementation details / Known issues
- run_monitoring.py は監視用 DB の初期化（init_monitoring_db）を行うが、Monitoring テーブル定義などの実装は別モジュール（kabusys.monitoring.*）に依存する。
- run_execution.py は BrokerClientFactory を利用し、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使う前提（実装は外部モジュールに依存）。
- Settings の .env 自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- config._parse_env_line はクォート付き値のエスケープやコメント処理をかなり丁寧に扱うが、すべての .env 形式を完全に網羅しているわけではない。
- portfolio.position_sizing には「銘柄別単元（lot_size）を将来的に拡張する」旨の TODO が残る。
- portfolio.risk_adjustment.apply_sector_cap は sector_map にキーが存在しない場合 "unknown" 扱いとしてセクター上限を適用しない実装となっている（意図的）。
- research/factor_research.py は末尾で実装が途中で切れている（未完了）。将来的に DuckDB 上の prices_daily / raw_financials を参照して完全実装する予定。
- logging_setup では stdout を主要なコンソール出力先にしている（cron 等で stdout/stderr を一本化する運用を想定）。
- process_priority.set_process_priority は権限不足や未対応 OS の場合に安全にスキップする実装（警告ログ）。

今後の予定（短期）
- research/factor_research.py の完成（ファクター計算全実装）。
- monitoring / execution の依存モジュール（monitoring.system_monitor, execution.engine 等）の結合テストとドキュメント整備。
- 銘柄別 lot_size 対応や手数料・スリッページの詳細パラメータ化。
- Paper Trading 検証レポートの自動化・CI 結合（定期実行ジョブ化）。

--------------------------------------------------------------------------------
参考: リポジトリ内の主なエントリポイント・CLI
- python -m kabusys.config_setup        (.env ウィザード)
- python -m kabusys.validate_config     (設定検証 CLI)
- python -m kabusys.run_execution       (ExecutionEngine 起動スクリプト)
- python -m kabusys.run_monitoring      (SystemMonitor ポーリング起動スクリプト)
- python -m kabusys.tools.paper_verification_report  (Paper Trading レポート)