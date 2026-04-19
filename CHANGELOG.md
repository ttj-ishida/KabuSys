CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
（https://keepachangelog.com/ja/）

Unreleased
----------

- なし

0.1.0 - YYYY-MM-DD
------------------

Added
- 基本アプリケーションを初期リリース
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動を実装。
    - 停止フラグ (data/stop_requested.flag) と実行中 PID ファイル(data/execution.pid) の扱いに対応。停止フラグ検知でエンジンを安全に停止。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) 検知でループを終了。
- 設定管理
  - config.py: 環境変数/.env の読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込み機能を提供。
    - .env 読み込みは .env → .env.local の順で適用。OS 環境変数は保護され上書きされない。
    - 複数の設定プロパティを提供（DB パス、PID/kill flag パス、しきい値、Paper Trading 関連設定、LOG_LEVEL など）。PAPER_FILL_MODE の妥当性チェックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 対話で主要設定項目を入力し .env ファイルを生成。既存値の読み込み、シークレットのマスク表示、保存前の確認を実装。
- 設定検証ツール
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境時のガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定する共通関数 setup_logging を追加。
    - ログディレクトリ作成失敗時にはファイル出力を無効にしコンソール出力のみで継続。
    - ログレベルおよびログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - Windows と POSIX を吸収するプロセス優先度設定（set_process_priority）を実装。アクセス権限不足等は警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を追加（指定コア数でのピン留め、例外時は警告）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別上限（max_sector_pct）を適用して候補をフィルタリング。sell_codes を当日売却除外として扱う。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。単元株（lot_size）、per-stock 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を加味した保守的見積り、端数配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。--from/--to/--db オプションをサポートし、SQLITE の trade_logs/system_status/risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
    - P95 計算、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義。
- 研究用ファクター計算（骨組み）
  - research/factor_research.py:
    - モメンタム／ボラティリティ等の計算設計と定数を追加。DuckDB 接続を受ける設計（prices_daily / raw_financials を想定）。一部実装（関数の骨組み）は追加済み（未完）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Known issues / Notes
- research/factor_research.py は途中までの実装（ファイル末尾で切れている）。完全な指標計算は今後の実装予定。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバックなど）を残しています。
- process_priority/set_cpu_affinity は権限やプラットフォームの違いで動作しない場合があり、その場合は警告を出して処理を継続します。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布形態によっては自動ロードがスキップされる場合があります（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用）。

Security
- なし

----------

今後の予定（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity 等の出力）。
- ExecutionEngine 周りの統合テストと PaperTrading のより詳細な挙動検証。
- logging / monitoring のメトリクス強化と LINE 通知連携の実装。