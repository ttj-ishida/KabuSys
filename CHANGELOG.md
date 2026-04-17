# Changelog

すべての変更は Keep a Changelog の形式に従います。  
次のリリースはセマンティックバージョニングに基づき管理してください。

## [0.1.0] - 2026-04-17

### Added
- 初期リリースを公開。
- 実行用エントリポイントを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト。起動時にプロセス優先度を High に設定し、BrokerClientFactory を用いて環境（KABUSYS_ENV）に応じたブローカークライアントを生成。paper_trading モードでは専用の paper_trading DB を使用し、本番 DB と分離する。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 環境設定周りの CLI を追加:
  - config_setup.py — 対話式ウィザードで .env を初期作成／更新できる。必須／任意項目の管理、シークレットマスキング、デフォルト値の提示等を実装。
  - validate_config.py — .env と config/*.yaml の事前検証 CLI。必須環境変数チェック、KABUSYS_ENV 値チェック、YAML パース（PyYAML が存在する場合）、本番環境向けのガードチェック（LINE トークンや Kill Switch 設定）などを提供。--strict オプションで警告も失敗扱いにできる。
- 環境変数読み込み／設定管理:
  - config.py — .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。.env ファイルの詳細なパースロジック（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ローディング無効化に対応。Settings クラスで各種設定プロパティ（DB パス、API トークン、紙取引設定、監視閾値など）を提供。
- ポートフォリオ構築ライブラリ（純粋関数群）を追加:
  - portfolio/portfolio_builder.py — シグナル選定（スコア降順、同点タイブレーク）と重み算出（等金額、スコア加重。スコア全て0時は等配分にフォールバック）。
  - portfolio/risk_adjustment.py — セクター集中制限（既存保有を考慮して新規候補を除外）とレジーム乗数（bull/neutral/bear に応じた投下資金倍率、未知レジームはフォールバック）。
  - portfolio/position_sizing.py — 各種配分メソッド（risk_based, equal, score）に基づく発注株数算出。単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）によるスケールダウン、コストバッファの考慮、残余の配分ロジック等を実装。
  - portfolio/__init__.py で上記関数群をエクスポート。
- 実用ユーティリティ:
  - utils/process_priority.py — psutil を利用したクロスプラットフォーム（Windows / POSIX）向けプロセス優先度制御と CPU affinity 設定ユーティリティを導入。未対応 OS や権限不足時に安全にスキップする堅牢性を有する。
- リサーチモジュール:
  - research/factor_research.py — DuckDB 上の prices_daily / raw_financials を参照してファクター（モメンタム、移動平均乖離、ATR、出来高指標など）を計算する関数群を提供。営業日ベースのウィンドウ処理、欠損データ対応を含む。
- 運用レポート:
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプト。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 を含む）を集計し PASS/FAIL を判定する。デフォルト閾値（稼働率99%、注文成功率90% など）を定義。SQLite DB の存在チェックや SQL 実行時の OperationalError に対するフォールバックを実装。

### Changed
- なし（初回リリースのため差分なし）。

### Fixed
- なし（初回リリース）。

### Security
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env を Git にコミットしないこと）。

### Notes / Design decisions
- run_monitoring と run_execution は起動直後にプロセス優先度を "high" に設定する設計。権限不足やプラットフォーム差異は警告で済ませることで起動失敗を避ける。
- run_execution は paper_trading モード時に MockBrokerClient を使用して paper_trading 用 DB に記録する（本番 DB と完全分離）。
- .env パースは現実的な記法（export プレフィックス、クォート、エスケープ、コメント）に対応しており、OS 環境変数を保護するための protected 機構を備える。
- portfolio / position_sizing の設計は将来的に銘柄別 lot_size のサポートや価格フォールバックを導入する余地を残している（TODO コメントあり）。
- process_priority と CPU affinity の設定は権限や環境による例外を捕捉し、安全にフォールバックする。

もしリリースノートを英語や別フォーマットで出力したい、あるいは項目を細分化（例えば「Monitoring」「Execution」「Portfolio」「Tools」ごとに詳細な変更点）したい場合は指示してください。