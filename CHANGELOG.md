# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  

現在のバージョン: 0.1.0 — 2026-04-25

## [0.1.0] - 2026-04-25

### Added
- プロジェクトの初回リリース。以下の主要機能・モジュールを追加。
- 起動スクリプト・ランタイム
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。0 以下の値はデフォルトにフォールバックして警告を出す。
    - 停止検知はプロジェクトルート下の data/stop_requested.flag を参照。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して初期化。
    - SQLite / DuckDB へ接続して監視データ格納を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。
    - スレッドでエンジンを起動し、停止フラグ検知で安全にシャットダウンする仕組みを実装。

- 設定・検証・セットアップ
  - config.py
    - .env ファイルおよび環境変数からの設定読み込みを実装。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env 読み込み。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックスやクォート／エスケープ、インラインコメントに対応する堅牢な実装。
    - Settings クラスを追加し、各種設定（DB パス、LINE トークン、監視閾値、環境フラグなど）をプロパティで提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - J-Quants / kabuAPI / DB パス / ログレベル / Kill Switch など主要項目の入力補助とテンプレート出力を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数や KABUSYS_ENV, LOG_LEVEL, DB パスの存在確認、PyYAML がある場合は YAML のパース検証を行う。
    - KABUSYS_ENV=live の際の追加ガード（LINE 通知設定未設定や Kill Flag 自動クリア設定への警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全スコアが 0.0 の場合に等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を追加。既存ポジションのセクター時価総額から過剰セクターを検出して新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" を想定。未知値は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベースの株数計算、単元株（lot_size）丸め、1 銘柄上限・利用率上限の適用、aggregate cap によるスケールダウンと端数再配分アルゴリズムを実装。
    - 手数料・スリッページ推定用の cost_buffer を考慮。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続するフォールバックを実装。
    - ログレベルとログディレクトリの解決順を仕様化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - プロセス優先度（Windows と POSIX を吸収）設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - psutil の権限不足や未サポート環境では警告を出して安全にスキップ。

- 分析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し、PASS/FAIL を判定する。
    - フィルタ期間指定（--from / --to）と DB パス指定（--db、環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - P95 計算、N/A 表示などのフォーマット関数を実装。
  - research/factor_research.py （ファクター計算基盤）
    - Momentum / Value / Volatility / Liquidity の設計方針と計算方針を実装するためのモジュール追加。
    - DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを計算する設計（calc_momentum の実装開始）。※ファイル末尾が途中で切れており、calc_momentum の実装が継続中。

- パッケージ初期化
  - __init__.py によるバージョン設定 (__version__ = "0.1.0") と公開 API (__all__) の追加。

### Changed
- n/a（初回リリースのため変更履歴はありません）。

### Fixed
- n/a（初回リリースのため修正履歴はありません）。

### Deprecated
- n/a

### Removed
- n/a

### Security
- n/a（セキュリティ関連の既知の変更はありませんが、.env の取り扱いについては .env を絶対に Git に含めない旨を config_setup のテンプレートに明記）。

Notes / 実装上の注意事項
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に動作させる際は KABUSYS_DISABLE_AUTO_ENV_LOAD の活用や明示的な環境変数設定を推奨します。
- monitoring は設計上、本番用の sqlite_path を参照します。開発やテストで分離したい場合は環境変数で sqlite_path を切り替えてください。
- research/factor_research.py は現状で一部実装が途中（calc_momentum の実装継続が必要）です。運用前に該当部分の完成を確認してください。

もし特定の変更点をより詳細に分解したい、あるいは未完成箇所（factor_research など）を TODO リスト化してほしい場合は、その旨を教えてください。