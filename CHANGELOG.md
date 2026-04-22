CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-22
-------------------
初回リリース。プロジェクトのコア機能とユーティリティ群を実装。

Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理
  - 環境変数/.env 読み込みモジュールを実装（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順をサポート。OS 環境変数の保護（上書き防止）。
    - 複数のパースルール（export プレフィックス、クォートのエスケープ、インラインコメント処理）に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
    - Settings クラスで各種設定プロパティを提供（JQUANTS, kabu API, DuckDB/SQLite パス, paper trading 関連, 監視閾値など）。入力値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。

- CLI / ユーティリティ
  - 環境設定ウィザード CLI（kabusys.config_setup）を追加。
    - 対話式で .env を作成/更新。各項目の説明・デフォルト値・シークレット扱いを実装。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）、本番環境向けガード（LINE 設定や Kill Switch の注意）を実装。
    - --strict モードで警告を FAIL 扱いにできる。

- 起動スクリプト / デーモン
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - stop_requested.flag による外部停止フラグを監視。
    - SystemMonitor の一回実行 check_once() をループで呼び、例外はログに記録して継続。
    - duckdb/SQLite 接続の初期化（init_monitoring_db）を実行。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient 適用想定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - RiskManager に渡すデフォルト構成値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定。
    - デーモンはスレッドで実行され、stop_requested.flag によって停止。execution.pid の取り扱いをサポート。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築（pure functions）
  - kabusys.portfolio モジュールを実装（pure function ベース、DB 参照なし）。
    - portfolio_builder:
      - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で上位 N を選択。
      - calc_equal_weights: 等金額配分（1/N）。
      - calc_score_weights: スコア加重（全スコアが 0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment:
      - apply_sector_cap: 現行保有と価格からセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 にフォールバック。
      - 実装内に注記（TODO）: 価格欠損時のフォールバック戦略が未実装。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") をサポートし、lot_size（単元）に基づいた株数計算、per-stock 上限・aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料／スリッページ見積）を考慮したスケーリングと端数処理を実装。
      - risk_based モードでは risk_pct / stop_loss_pct を用いたポジションサイズ計算を実装。
      - 将来的な拡張のための注記（銘柄ごとの lot_size を持たせる TODO）を含む。

- リサーチ / ファクター計算（骨格）
  - kabusys.research.factor_research を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - モメンタム計算の定数（1M/3M/6M, MA200, ATR など）を定義し、calc_momentum の骨格を実装（詳細は実装継続中）。

- ログ・プロセスユーティリティ
  - logging_setup（kabusys.utils.logging_setup）を追加。
    - ルートロガーに stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - process_priority（kabusys.utils.process_priority）を追加。
    - Windows (psutil 定数)、POSIX（nice 値）に対応した優先度設定（high/normal/low）。
    - set_cpu_affinity によるプロセスの CPU 固定（最初 N コア）をサポート。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- モニタリング用 DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を参照する起動フローを実装（両スクリプトで監視テーブルが存在することを保証するために呼び出し）。

- ユーティリティツール
  - tools.paper_verification_report を追加。
    - Paper Trading の検証レポートを生成する CLI。PAPER_TRADING_SQLITE_PATH（または --db オプション）からデータを集計。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ等を計算。
    - 標準の閾値と PASS/FAIL 判定を実装（稼働率 >= 99.0%, fill >= 90%, send >= 95%, P95 <= 200 ms）。
    - 日付フィルタ (--from / --to) をサポート。
    - P95 計算、SQL 抽出、N/A 表示ロジックなどを実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Known limitations
- 一部モジュール（factor_research など）は骨格実装に留まる箇所がある。
- apply_sector_cap / position_sizing の一部で価格欠損時のフォールバック（前日終値等）は未実装（TODO コメントあり）。
- process_priority や set_cpu_affinity は権限不足やプラットフォーム制限により動作しない場合、警告を出して安全にスキップする設計。
- ログディレクトリの作成に失敗するとファイル出力は無効化されるが、stdout ログは継続される。

References
- 環境変数の主なデフォルト値:
  - MONITOR_POLL_INTERVAL: 60 (秒)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID / stop flag / log ディレクトリは data/, logs/ をデフォルトで使用

もし差分の粒度をもっと細かく（ファイル単位の追加/変更一覧や設計上の意図など）記載したい場合は、どのレベルまで詳細化するかを教えてください。