CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル data/stop_requested.flag による安全停止対応。
  - 監視用 DB は環境にかかわらず production の sqlite_path を使用する実装上の挙動（注意点あり）。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離。
  - BrokerClientFactory を介したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler といった依存コンポーネントの組み立て、スレッドによる実行監視、停止フラグによる安全停止をサポート。
- config.py: 設定管理クラス Settings を導入。
  - .env / .env.local の自動読み込み（プロジェクトルート検出ロジック付き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり。
  - 必須・任意設定のプロパティ（J-Quants / kabu API / DB パス / PID ファイル / 監視閾値等）を提供。
  - PAPER_FILL_MODE 等の値検証を実装（無効値で例外）。
  - env 判定（development/paper_trading/live）とログレベル検証を組み込み。
- config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
  - 主要な環境変数をユーザー入力で設定・保存する機能（既存 .env の読み込み・マスク表示・デフォルト提示・保存確認）。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスと config/*.yaml の存在・パース検証（PyYAML がなければ警告）、本番環境時の追加ガードチェックを実装。
  - --strict オプションで警告を FAIL 扱いにできる。
- utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
  - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log）。
  - LOG_DIR / LOG_LEVEL の解決順、ディレクリ作成失敗時のフォールバック（コンソール出力のみ）を考慮。
- utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
  - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度を設定。失敗時は警告で続行。
  - set_cpu_affinity によるコア固定 (first N cores) 機能。
- portfolio/*: ポートフォリオ構築関連の純粋関数群を追加。
  - portfolio_builder: シグナル選定（select_candidates）・等分配（calc_equal_weights）・スコア加重（calc_score_weights）。
  - risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 単元株丸め、risk_based / equal / score に応じた発注株数計算、aggregate cap（available_cash 超過時のスケールダウン）と残差処理の実装。
- tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定するレポートを標準出力に生成。
  - P95 計算、期間フィルタ、DB パスのオプション/環境変数指定をサポート。
- research/factor_research.py: ファクター計算モジュール（Momentum 等）の骨組みを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
  - モメンタム・MA・ATR 等の定数・設計方針を含む。実装は継続中の箇所あり（未完の行あり）。

Changed
- パッケージメタ: __version__ を 0.1.0 に設定（初期バージョン）。
- ロギング: ログ出力は stdout を優先（cron/Task Scheduler の取り扱いのため）。ファイル出力は日次ローテーションで 30 日保持に設定。

Fixed
- 設定ロードの堅牢性向上: .env 読み込みで export プレフィックスやクォート・エスケープ、インラインコメントを正しく扱うようにした。

Breaking Changes
- run_monitoring の DB 動作: 監視（monitoring）は "環境にかかわらず" Settings.sqlite_path（本番監視 DB）を使用する実装になっています。開発/ペーパートレード環境で監視 DB を分離したい場合は設定の見直しが必要です（注意点として明示）。

Security
- シークレット系環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は config_setup の対話でマスク表示され、Settings から取得時は必須チェックで未設定時に明示的なエラーを出すようになっています。

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース相当の機能をまとめて追加（上記 Unreleased の主要項目を含む）。
  - 実行・監視のランチャー（run_execution.py, run_monitoring.py）
  - 環境設定管理（config.py）、対話式ウィザード（config_setup.py）、検証ツール（validate_config.py）
  - ロギング/プロセス管理ユーティリティ（utils/）
  - ポートフォリオ構築、リスク調整、ポジションサイジング（portfolio/）
  - Paper Trading 用検証レポート（tools/paper_verification_report.py）
  - 研究用ファクター計算モジュール（research/factor_research.py の骨組み）
  - パッケージ情報（__init__.py で __version__=0.1.0）

Changed
- ドキュメント参照: 各モジュール内に PortfolioConstruction.md / StrategyModel.md 等の参照記載を追加（実装設計の根拠として明記）。

Notes / 注意事項
- PAPER_FILL_MODE や KABUSYS_ENV 等、環境変数に対する値検証を厳密化しています。不正な値は起動時に例外を投げるため、.env の調整が必要になる場合があります。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、標準出力のみで運用されます（setup_logging でフォールバック）。
- research/factor_research.py は設計方針と定数・API を定義済みですが、ファクター計算の詳細実装は引き続き整備が必要です。

過去のリリース
---------------
- （なし）初回リリースのため履歴なし。

---- End of CHANGELOG ----

（必要であれば、各ファイルのコミット単位やより細かな変更点を追記できます。追記希望があれば該当箇所を指定してください。）