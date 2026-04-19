# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。
リリースに関する情報はコードベースから推測した内容を記載しています。

現在のバージョン: 0.1.0

## [Unreleased]
- ドキュメント的な注記や内部ログ文言の小修正（詳細はコミットログ参照）。
- research/factor_research.py の一部が未完の状態（計算ロジックの続きが存在する見込み）。今後のリリースで完成予定。

---

## [0.1.0] - 2026-04-19
初回リリース（推定）。日本株自動売買フレームワーク「KabuSys」の基本機能群を実装。

### Added
- 実行スクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）で完全に分離して運用。
    - 起動時にプロセス優先度を高（high）に設定。
    - 停止フラグ (data/stop_requested.flag) により安全に停止可能。PID ファイル (data/execution.pid) をサポート。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する旨の設計。

- 設定管理
  - config.py：環境変数/.env のロードおよび Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルートが特定できる場合に .env, .env.local を読み込む）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 各種設定プロパティ（DB パス、API トークン、ENV 判定、紙トレード設定等）を提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH をサポート。
  - config_setup.py：対話式 .env 作成ウィザードを実装（python -m kabusys.config_setup）。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の設定を対話的に入力・保存可能。
  - validate_config.py：起動前設定検証 CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV, LOG_LEVEL の検証、DB パス親ディレクトリの確認、config/*.yaml 存在チェック（PyYAML があればパースも検証）、本番環境向けのガード等。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投資乗数。
  - portfolio.position_sizing
    - calc_position_sizes: 単元株丸め・リスクベース／等配分／スコア配分に対応した発注株数算出。aggregate cap（利用可能現金を超える場合のスケーリング）、lot_size（単元）考慮、コストバッファ対応等を実装。

- ユーティリティ
  - utils/logging_setup.py：統一ログ設定ユーティリティ
    - コンソール (stdout) 出力 + 日次ローテーションのファイル出力（logs/<app_name>.log、30日保持）。
    - LOG_DIR / LOG_LEVEL の環境変数に対応。既存ハンドラの二重設定回避。
  - utils/process_priority.py：プラットフォーム非依存のプロセス優先度・CPU affinity 設定ユーティリティ
    - Windows / POSIX（Linux, Darwin, FreeBSD）での優先度設定をラップ、アクセス権限不足等は警告でフォールバック。
    - set_cpu_affinity によるコアピン固定機能。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs などのテーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し PASS/FAIL を判定。
    - しきい値（稼働率 99% etc.）と判定ロジックを実装。日付フィルタ / DB パス指定オプションを提供。

- 研究用モジュール
  - research/factor_research.py：DuckDB を用いたファクター計算機能（Momentum, Value, Volatility, Liquidity）を実装するための骨格と定数を追加（prices_daily / raw_financials を想定）。現状一部実装済み、続きあり。

### Changed
- パッケージ初期化
  - __init__.py にて __version__ = "0.1.0" を設定。主要サブパッケージを __all__ でエクスポート。

### Fixed
- 環境ファイルのパース堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応等を実装し .env パーサの堅牢性を向上。

### Notes / Usage
- 環境変数/設定
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を読み込みます。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL（秒）で調整可能（デフォルト 60）。
  - Paper Trading 用挙動は KABUSYS_ENV=paper_trading にて有効化され、Paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。

- 実行コマンドの例
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Known limitations / TODO
- research/factor_research.py はファクター計算の全ロジックが未完（ファイル末尾が途中）。今後のリリースで完成予定。
- position_sizing の price のフォールバック（価格が欠損した場合の前日終値等）は TODO コメントあり。価格データ欠損時の挙動に注意。
- 一部の外部依存（psutil, duckdb, PyYAML）が環境にない場合は機能が限定される。validate_config は PyYAML が無い場合に YAML 検証をスキップして警告を出す。

---

開発者向け補足:
- 重大な API 変更や破壊的変更がある場合は次回リリースで明示的に記載します。