CHANGELOG
=========

すべての重要な変更履歴をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。
（注: 以下の履歴は提示されたコードベースの内容から推測して作成しています。）

Unreleased
----------

- ドキュメントや内部コメントの改善、軽微なリファクタ（実装上の目視での差分のみ）。
- テストカバレッジや CI/CD スクリプトの追加（ソースコードには含まれていないため推測）。

0.1.0 - 2026-04-17
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基盤機能を追加。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。以下の機能を持つ:
    - 環境設定に応じた SQLite パス選択（paper_trading 実行時は専用 DB を使用して本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) 検出による安全な停止、PID ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。以下の機能を持つ:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用する設計（環境にかかわらず監視 DB に書き込む）。
    - 停止フラグでループ終了、例外ハンドリングでループ継続。
- 設定管理
  - config.py: Settings クラスを追加。環境変数を型化して取得するプロパティを提供（DB パス、API トークン、監視閾値等）。
  - .env 自動読み込み機構を実装（プロジェクトルートの検出、.env / .env.local の読み込み順、OS 環境変数保護）。
  - .env パースは export プレフィックス・クォート・コメントなど多様な書式に対応。
- 設定ユーティリティ CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。シークレット扱いやデフォルト提示、最終確認・保存機能。
  - validate_config.py: 起動前チェック用 CLI。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在と（可能なら）YAML パース検証、live 環境向けの追加警告を実装。--strict モードで警告を失敗扱いに可能。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナルの選定 (select_candidates) と配分重み計算 (calc_equal_weights, calc_score_weights)。
  - portfolio.position_sizing: 複数の allocation_method（"risk_based", "equal", "score"）に対応した発注株数計算。単元株丸め、単銘柄上限・総投下上限（aggregate cap）、コストバッファ考慮によるスケーリングロジックを備える。
  - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたモメンタム・ボラティリティ等のファクター計算関数（calc_momentum, calc_volatility 等）。prices_daily / raw_financials テーブルのみ参照し、SQL ウィンドウ関数を活用。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティ。Windows と POSIX（Linux, macOS 等）を吸収し、権限不足や未対応 OS は警告してスキップ。
- モニタリング DB 初期化ヘルパー
  - monitoring.monitoring_db:init_monitoring_db を利用して監視テーブルの冪等な初期化を行う（run_* スクリプトから呼び出し）。
- ツール
  - tools.paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。期間指定や DB パス指定（引数 / 環境変数）に対応。指標として稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（PASS/FAIL）判定を行う。

Changed
- N/A（初回リリースのため既知の変更履歴なし）.

Fixed
- N/A（初回リリースのため既知の修正履歴なし）.

Security
- config_setup にて .env ファイル生成時にシークレット項目は表示をマスク（表示時）する方針を採用。
- .env ファイル生成時の注意書きで Git へコミットしないことを明示。

Notes / Behaviors
- Paper Trading 分離: paper_trading 環境では Execution 用の SQLite DB を専用ファイル（デフォルト data/paper_trading.db）に分離し、本番データと混ざらないよう設計。
- MONITOR_POLL_INTERVAL の不正値は警告されデフォルト（60 秒）へフォールバック。
- PAPER_FILL_MODE は明示的に有効値チェック（instant, partial, never, reject）を行い、不正値は例外を送出。
- process_priority は権限不足や未対応プラットフォームで安全にフォールバックして実行を継続する。
- validate_config は PyYAML 未導入時にも動作し、YAML 内容検証はスキップして警告を出す。

開発者向けメモ（推測）
- DuckDB を分析系に、SQLite を監視・発注ログに使う二層構成。
- ExecutionEngine 側の詳細実装（発注フロー・フェイルセーフなど）は別モジュールに実装されている想定（今回提示コードでは起動・組み立てロジックが確認できる）。
- 将来的に単元株（lot）を銘柄別に管理する拡張や価格フォールバックロジック（risk_adjustment 内の TODO）が検討されている。

導入・実行方法の要点
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

（以上）