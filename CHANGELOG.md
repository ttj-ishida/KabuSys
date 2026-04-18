CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回リリースを追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。ExecutionEngine をスレッドで起動し、data/execution.pid を使用して PID を管理。停止は data/stop_requested.flag を監視して安全に行う。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（Mock を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、RiskConfig／EngineConfig を用いた初期化。
    - 起動時にプロセス優先度を "high" に設定（psutil を利用、プラットフォーム差分を吸収）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
    - data/stop_requested.flag の検出でループを終了。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - 環境変数読み込みの細かいパーシングに対応（export プレフィックス、クォート、インラインコメント処理など）。
    - Settings クラスを導入し、各種設定プロパティ（DB パス、API トークン、監視閾値、環境種別判定等）を提供。PAPER_FILL_MODE のバリデーション等を実装。
    - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。デフォルト値、シークレットマスク表示、.env への安全な書き出しをサポート。
  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数・KABUSYS_ENV 値・DB パス・config/*.yaml の存在（および PyYAML があればパース検証）などをチェック。--strict オプションで警告を FAIL 扱い可能。
    - 本番環境用の追加ガードを実装（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告など）。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーへ設定。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）を吸収。psutil のアクセス制限や未対応環境は警告でスキップ。
    - CPU affinity 設定用 set_cpu_affinity を提供（任意）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額/スコア加重の重み算出 calc_equal_weights / calc_score_weights を追加。スコアが全て 0 の場合は等金額へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap と、市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加（regime によるマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - position sizing の実装を追加。allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファ（cost_buffer）を考慮した aggregate cap のスケーリングを実装。スケールダウン時に fractional 残差を考慮して追加配分するロジックを備える。
- Research・分析
  - research/factor_research.py（モジュール追加）
    - Momentum 等の定量ファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。（モジュールは関数群の雛形・実装方針を含む）
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を参照し、稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。日付フィルタ（--from / --to）と --db オプションをサポート。
    - P95 計算ユーティリティ、閾値（稼働率 99%、成功率 90% など）を組み込み。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

Notes / 実運用上の注意
- run_monitoring は監視データベース接続に settings.sqlite_path を用いるため、監視 DB は環境にかかわらず本番用設定と同じパスを参照します。テスト環境で監視 DB を分離したい場合は sqlite_path の環境変数を別途指定してください。
- run_execution は paper_trading モード時に paper_sqlite_path を使って本番 DB と完全に分離する設計です。ペーパートレード運用時は PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- .env ファイルはセキュリティ上 Git にコミットしないこと。config_setup により生成した .env ヘッダにもその旨を明示しています。
- プロセス優先度設定や CPU affinity は OS 権限により失敗する場合があり、その場合は警告を出してスキップする仕様です。

もし特定ファイルの変更点を詳しく分解したい、あるいは RELEASE NOTES を英語で用意したい場合は指示してください。