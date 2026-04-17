# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

### Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine の起動エントリポイント。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用し、MockBroker を利用することで本番 DB と分離して実行できる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。

- 環境設定まわりの CLI を追加
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する機能。シークレット項目は表示をマスク。
  - validate_config.py: .env と config/*.yaml の設定を起動前に検証する CLI。`--strict` モードで警告をエラー扱いにできる。

- 設定管理 API を追加
  - config.Settings: 環境変数からアプリ設定を取得するラッパー。自動でプロジェクトルートの .env / .env.local を読み込み（OS 環境変数を保護）、各種検証（値の範囲や列挙型チェック）、path の expanduser を行うプロパティ群を提供。

- Paper Trading 用レポート機能を追加
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成するコマンドラインツール（期間指定可）。稼働率 / 注文成功率 / 送信率 / レイテンシ (P95) などを集計して PASS/FAIL を判定する。

- ポートフォリオ構築用モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮）。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を用いたモメンタム・ボラティリティ等のファクター計算関数を追加（prices_daily / raw_financials を参照）。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（および CPU affinity）の設定を行うユーティリティを追加。Windows / POSIX の差分を吸収し、失敗時は警告でフォールバックする。

### Changed
- .env の自動読み込み挙動
  - プロジェクトルートを .git または pyproject.toml を基準に探索するように変更。これにより CWD に依存せずにパッケージ配布後も自動ロードが動作しやすくなった。
  - .env の読み込み順序は OS 環境 > .env.local > .env。OS 環境は protected として上書きを防ぐ。

- 実行・監視の運用面改善
  - run_execution/run_monitoring 起動時に最初にプロセス優先度を "high" に設定するようにし、重要プロセスの応答性を向上。
  - run_monitoring は Monitoring 用 DB 初期化を行い、KABUSYS_ENV にかかわらず本番用 sqlite_path を使って監視テーブルの存在を保証する（冪等な初期化）。
  - run_execution は paper_trading の場合にデータベースを分離して使用（settings.paper_sqlite_path）することで、本番データと完全に分離。

- 設定パースの堅牢化
  - .env パース処理で引用符付き値のエスケープを考慮（バックスラッシュエスケープ対応）、インラインコメントの扱いを改善。export プレフィックスにも対応。
  - Settings のいくつかのプロパティで値検証を追加（PAPER_FILL_MODE の候補チェック、KABUSYS_ENV / LOG_LEVEL の列挙チェック）。

### Fixed
- ポーリング間隔の環境変数処理の安全化
  - MONITOR_POLL_INTERVAL が不正な値（0 以下や文字列）だった場合、デフォルト値（60 秒）にフォールバックするように変更。無効値では warning を出力して安全に継続。

- run_execution/run_monitoring の停止管理
  - プロジェクト直下 data/stop_requested.flag を基に外部からの停止要求を検知して安全にシャットダウンする挙動を追加。ExecutionEngine ではスレッドを立て、フラグ検知で engine.stop() を経由して停止させる。

- position_sizing の割当ロジックの改善
  - aggregate cap によるスケーリングで単元株（lot_size）丸めを考慮し、端数の配分に対して残余キャッシュで再配分するロジックを導入。計算中に価格・単元未取得の場合はスキップして安全に動作。

### Security
- .env の生成テンプレートに注意喚起を追加（.env をコミットしないことを明記）。config_setup の出力でシークレットはマスク表示。

---

## [0.1.0] - 2026-04-17

最初の公開バージョン。以下を含む基本機能を実装。

### Added
- コアパッケージ初期構成
  - settings / config の読み込み、Settings オブジェクト
  - 自動 .env ロード機能（.env / .env.local）
  - config_setup (対話式 .env 作成) と validate_config (設定検証 CLI)
- 実行・監視エントリポイント
  - run_execution.py（ExecutionEngine 起動・paper_trading 分離）
  - run_monitoring.py（SystemMonitor ポーリングループ）
- ポートフォリオ構築ライブラリ
  - portfolio_builder, risk_adjustment, position_sizing の純粋関数群
- リサーチ & ファクター計算
  - research/factor_research.py（モメンタム・ボラティリティ等）
- Paper Trading 用ツール
  - tools/paper_verification_report.py（検証レポート生成）
- ユーティリティ
  - utils/process_priority.py（優先度 / CPU affinity）

### Changed
- DuckDB / SQLite 連携を採用（分析用に DuckDB、監視とペーパートレード用に SQLite を使用）
- 実行時のプロセス優先度設定を追加（起動直後に high を試行）

### Fixed
- .env パーサの堅牢化（引用符・エスケープ・コメント処理）
- 各種入力値の検証を強化（列挙型・閾値など）

---

注:
- 上記はソースコードから推測してまとめた変更履歴です。コミットログではなく機能面・振る舞いから記述しています。必要であれば個別ファイルごとの詳細や例、注意点などを追記します。