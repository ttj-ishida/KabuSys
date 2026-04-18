# CHANGELOG

すべての重要な変更を追跡します。フォーマットは Keep a Changelog に準拠しています。  
主な目的はリリースノートと、コードベースから推測される追加・修正点の説明です。

注意: 本ファイルは提供されたソースコードの内容から推測して作成しています。実際のコミット履歴や意図とは差異がある可能性があります。

## [Unreleased]

### Added
- 新しい起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用のエントリポイントを追加。プロセス優先度設定、DB 初期化、BrokerClientFactory 経由のブローカ接続、ExecutionEngine のスレッド実行・停止制御を実装。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用する（本番 DB と完全分離）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによりループ終了を行う。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。

- 環境設定関連の CLI・ユーティリティを追加
  - config_setup.py: .env の初期作成・更新を対話式で支援するウィザードを追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。--strict オプションで警告をエラー扱いにできる。PyYAML 未インストール時のフォールバックや本番向けの警告（LINE 設定や Kill Switch の注意）を含む。

- 設定読み込み / 管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートの検出、.env / .env.local の読み込み）。高度な .env パーサを実装し、export プレフィックス、引用符・エスケープ、インラインコメントの扱いに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。Settings クラスで各種設定プロパティ（パス、閾値、環境種別、paper_trading 用 DB パス等）と妥当性検査を提供。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。ログレベル・出力先は引数または環境変数で上書き可能。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows と POSIX を吸収し、権限不足等は警告にフォールバック。

- ポートフォリオ構築関連の純粋関数群を追加（DB 不使用）
  - portfolio/portfolio_builder.py: 候補銘柄選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) の実装。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) の実装。レジーム乗数は "bull"/"neutral"/"bear" をサポートし、未知のレジームはフォールバックで 1.0（警告ログ）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポート。最大ポジション比率、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積）を考慮した安全な割付処理を実装。価格欠損時のスキップや再配分ロジックも実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite データベースから稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計しレポートを出力するツールを追加。閾値に基づく PASS/FAIL 判定を行い、--from/--to/--db オプションをサポート。

- その他
  - package の __version__ を 0.1.0 に設定（初期バージョン）。
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（momentum 等の指標計算を想定）。（実装はモジュール内で継続中/未完の箇所がある）

### Changed
- なし（初期追加が中心のため）

### Fixed
- なし（初期追加が中心のため）

### Security
- なし

---

## [0.1.0] - 2026-04-18

リリース: 初期公開リリース（推定）。上記の主要機能群をパッケージ化。

### Added
- 初回リリースとして以下を含む:
  - ExecutionEngine 起動スクリプト(run_execution)
  - SystemMonitor 起動スクリプト(run_monitoring)
  - 環境設定管理（config.py）, ウィザード(config_setup), 検証ツール(validate_config)
  - ロギング設定ユーティリティ (utils/logging_setup)
  - プロセス優先度 / CPU affinity ユーティリティ (utils/process_priority)
  - Portfolio 構築ライブラリ（portfolio/*）: 候補選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数
  - Paper Trading 検証レポートツール (tools/paper_verification_report)
  - research.fator_research の雛形
  - パッケージメタ情報 (__version__ = 0.1.0)

### Changed
- なし

### Fixed
- なし

### Security
- なし

---

注意事項・補足
- run_monitoring は説明の通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する仕様になっています。本番ポリシー上の意図に注意してください（paper_trading での完全分離が必要な場合は別途設計が必要）。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、環境変数を明示的にセットしてください。
- research/factor_research.py はモジュールの一部で実装が途中に見えるため、リリース後に追加実装・テストが必要です。
- 実装中の各モジュール（特に Execution / Broker 周り）は外部リソース（ブローカー API、SQLite/DuckDB、psutil 等）に依存するため、運用環境では設定・権限・テストを十分行ってください。

この CHANGELOG はソースコードからの推測に基づき作成しました。実際のコミットメッセージや意図に合わせて適宜修正してください。