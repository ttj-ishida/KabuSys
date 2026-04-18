CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

Unreleased
----------

- ドキュメント・メタ情報の更新や軽微な内部改善を予定。

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース。KabuSys 自動売買基盤のコアユーティリティと CLI を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を設定し、スレッドでエンジンを実行。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを抽象化。RiskManager, OrderManager, Reconciler 等の組み立てを実装。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を利用した安全停止機構を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。プロセス優先度設定と監視 DB 初期化を実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番用 sqlite_path を使用する仕様。
- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順・保護（OS 環境変数を上書きしない）を実装。
    - Settings クラスを追加し、各種環境変数（J-Quants、kabuAPI、DBパス、監視閾値など）の取得と検証を提供。
    - PAPER_FILL_MODE や KABUSYS_ENV などの入力検証を実装（不正値で ValueError を送出）。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。必須/任意項目、シークレット表示、保存確認を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数、パスの存在、config/*.yaml の存在とパース（PyYAML がある場合）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等比率（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元株丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリングを実装。
- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - Momentum, Volatility, Liquidity 等のファクター計算基盤を追加（DuckDB 接続を受け取り SQL で計算）。
    - mom_1m/mom_3m/mom_6m、MA200 乖離、ATR20、20日平均出来高などを計算。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を算出し PASS/FAIL 判定を行う。
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows の priority class、POSIX の nice を考慮）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（利用可能なコア数より多い指定時の挙動を考慮）。
- パッケージ初期化
  - __init__.py にバージョン 0.1.0 を設定。

Changed
- なし（初回リリースにつき既存機能の「追加」が中心）。

Fixed
- なし（初回リリース）。

Security
- なし特記事項。

Notes / 備考
- 設定と運用
  - デフォルトの DB/ファイルパスは data/ 下（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。運用環境では .env で明示的に指定することを推奨。
  - KABUSYS_ENV によって挙動が変わる（development / paper_trading / live）。paper_trading は発注と DB を分離するため安全に検証可能。
  - 本番運用時は KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（自動クリアは危険）。
- ロギング
  - 各 CLI/スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使用。LOG_LEVEL 環境変数で制御可能。
- 将来の改善点（TODO）
  - position_sizing: 銘柄別の lot_size を stocks マスタに持たせる拡張。
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）の利用。
  - research モジュールの追加ファクターや並列化、DuckDB クエリ最適化。

署名
----
この CHANGELOG はリポジトリ内のソースコードを解析して推測に基づいて作成した初期リリースノートです。必要に応じて実運用チームのリリース方針に合わせて調整してください。