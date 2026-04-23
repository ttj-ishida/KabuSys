# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
初回リリースとしてバージョン 0.1.0 を記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション骨格を実装
  - パッケージ情報: kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 環境設定管理
  - Settings クラス（kabusys.config）を実装。環境変数の取得・検証、デフォルト値の提供を行う。
  - .env 自動読み込み機能を実装（プロジェクトルート検出、.env/.env.local の読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 環境変数パースの堅牢化（クォート、エスケープ、インラインコメント処理対応）。
  - 各種設定プロパティを提供（DB パス、KABUSYS_ENV、PAPER_TRADING_SQLITE_PATH、PID/kill flag パス、監視閾値等）。
- インタラクティブ設定ウィザード（CLI）
  - kabusys.config_setup: .env を対話的に作成・更新するウィザードを実装。
  - 入力項目定義、既存 .env 読み込み、マスク表示（シークレット）、保存確認機能を提供。
- 設定検証 CLI
  - kabusys.validate_config: 起動前の設定検証ツールを実装。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの存在確認、config/*.yaml の存在・パースチェック（PyYAML 利用時）、本番用ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）を実装。
  - --strict フラグで警告を失敗扱いにできる。
- 実行エンジン起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを実装。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
  - BrokerClientFactory により実行時に適切なブローカークライアントを生成（paper/live の切替を想定）。
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
  - 停止フラグ（data/stop_requested.flag）検知で安全に停止。実行時の PID 管理（data/execution.pid）。
  - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
- 監視ループ起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告後デフォルトにフォールバック。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを記録（init_monitoring_db を呼出しテーブル存在を保証）。
  - 停止フラグ検出でループを終了。KeyboardInterrupt による終了処理も実装。
  - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）を実装。
    - stdout に出力する StreamHandler と、日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - ログレベルの解決順を実装（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。
    - Windows / POSIX を吸収し、高/通常/低優先度（nice 値 / Windows 定数）を設定。
    - CPU affinity を最初の N コアに制限する set_cpu_affinity を提供。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で並べ上位 N を返す（同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が上限 (max_sector_pct) を超える場合に同セクターの新規候補を除外（"unknown" セクターは対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ）考慮などを実装。
    - risk_based アルゴリズムでは stop_loss_pct と risk_pct を用いた株数算出。
- Paper Trading 検証レポートツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB からレポートを生成する CLI を実装。
  - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
  - デフォルトしきい値を定義し（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）、Pass/Fail 判定を出力。
  - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
- 研究モジュール（DuckDB ベースのファクター計算）
  - research.factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を導入（prices_daily / raw_financials テーブル参照）。（関数の一部実装を含む）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数が上書きされないよう protected set を導入（.env/.env.local 読み込み時）。

---

注意:
- monitoring 用 DB 初期化は init_monitoring_db(sqlite_conn) を通じて行われる（既存テーブルがあれば冪等的にスキップされることを想定）。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、権限不足等で設定に失敗した場合は警告を出してスキップします。
- .env ファイルには秘密情報（トークン・パスワード等）が含まれるため絶対にバージョン管理リポジトリへコミットしないでください（config_setup のヘッダにも注意書きあり）。

今後の予定（例）
- research.factor_research の完全実装（すべてのファクター計算の完成、Zスコア正規化統合）。
- ExecutionEngine / SystemMonitor の詳細実装と結合テスト。
- 単体テスト・CI の追加、およびドキュメント整備。