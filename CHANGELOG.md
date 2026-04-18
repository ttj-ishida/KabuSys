CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。
このプロジェクトの初回リリース: 0.1.0

Unreleased
----------

(現時点の unreleased 項目はありません)

0.1.0 - 2026-04-18
-----------------

Added
- プロジェクト初期版を追加。主要機能とユーティリティ群を収録。
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用する実行フローを実装。エンジンは別スレッドで稼働し、 data/stop_requested.flag を監視して安全に停止可能。PID ファイルサポートあり。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。data/stop_requested.flag による停止、MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）などをサポート。監視は環境にかかわらず本番用 sqlite_path を使用する挙動。
  - 設定関連:
    - config.py: Settings クラスを提供。.env 自動読み込み（.env -> .env.local、OS 環境変数を保護）、プロジェクトルート検出（.git / pyproject.toml）、細かな .env パース（クォート、エスケープ、インラインコメント対応）。各種設定プロパティ（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE 等）を公開。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装（secret マスキング、選択肢、デフォルト値、保存確認）。
    - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と（PyYAML がある場合の）パース検証、本番環境用ガードを実装。--strict オプションで警告を失敗扱いにできる。
  - ログ・プロセス管理ユーティリティ:
    - utils/logging_setup.py: 標準化されたログ設定ユーティリティを実装。stdout への StreamHandler（標準出力）と日次ローテーション（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決優先順をサポート。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - utils/process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを実装（Windows/Linux/macOS 対応、nice 値／HIGH_PRIORITY_CLASS を利用）。set_cpu_affinity で CPU affinity 固定機能も提供。権限不足や未対応環境では警告ログを出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群、DB 非依存）:
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコア合計が 0 の場合等分にフォールバック）を実装。
    - portfolio/risk_adjustment.py: セクター集中上限の適用（既存保有を考慮して新規候補を除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
    - portfolio/position_sizing.py: 発注株数計算ロジックを実装。risk_based / equal / score の割当方式、単元株丸め、1 銘柄上限・aggregate cap（利用可能現金の超過時スケーリング）、cost_buffer（手数料/スリッページ見積り）考慮、lot_size 固定対応。
  - リサーチ:
    - research/factor_research.py: ファクター計算（モメンタム・MA200乖離・ATR・流動性など）を行うモジュール（DuckDB 接続を受け、prices_daily/raw_financials を参照する設計）。（実装はファイルに含まれるが、一部省略・継続実装を想定）
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計・評価し PASS/FAIL を判定。閾値はソース内で定義（稼働率 99%、成功率 90% など）。--from/--to/--db オプション対応。

Changed
- 初回リリースのため変更履歴はありません（初期追加のみ）。

Fixed
- 初回リリースのため修正履歴はありません。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数の初期設定ウィザードで .env に秘密値を直接書き出す設計のため、.env を絶対に Git にコミットしない旨をドキュメントヘッダに明記（config_setup.py）。機密情報は運用で適切に管理してください。

Notes / 実装上の重要ポイント（運用者向け）
- run_monitoring は「監視用途の DB」として Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する設計になっています。必要に応じて環境変数でパスを切り替えてください。
- run_execution は paper_trading の場合に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離します。ペーパートレードの挙動は PAPER_FILL_MODE（instant/partial/never/reject）で制御できます。
- ログ設定はログディレクトリの作成に失敗した場合でもコンソールログにフォールバックします（ファイル出力は無効化）。これは cron 等の限定環境でも起動失敗しないための保険です。
- process_priority と CPU affinity は権限やプラットフォームに依存する操作です。失敗した場合は警告を出してスキップしますが、必要な場合は運用者側で適切な権限設定を行ってください。
- .env 自動読み込みはデフォルトで有効（.env → .env.local の順）。テスト等で自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向け補足
- Settings と settings（インスタンス）は config.py により提供されます。テスト時に環境操作が影響する場合は os.environ を操作するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動読み込みを抑制してください。
- portfolio/* の関数群は副作用を持たない純粋関数として設計されており、単体テストが容易です。
- validate_config の --strict フラグを使うと警告も失敗（exit 1）になります。CI でのチェックに利用できます。

--- 

今後の予定（例）
- research/factor_research の完全実装（ファクター計算の詳細実装完了）
- strategy / execution の詳細コンポーネントの単体テスト追加
- ログの構造化（JSON ログ）/ メトリクス出力（Prometheus 等）対応検討

（終わり）