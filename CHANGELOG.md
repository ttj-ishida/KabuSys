CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-17 (初回リリース)

Added
- 基本アプリケーション構成
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"。
  - 環境変数 / 設定管理モジュール (kabusys.config)
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、クォート（' "）およびエスケープ、インラインコメントの扱いに対応。
    - OS 環境変数は保護され、.env.local は .env を上書きする仕組みを提供。
    - Settings クラスで各種設定値をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
    - KABUSYS_ENV の妥当性チェックおよび is_live / is_paper / is_dev ヘルパーを導入。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。

- CLI ユーティリティ
  - 環境設定ウィザード (kabusys.config_setup)
    - 対話式に .env を生成・更新するウィザードを提供。主要な設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch の初期設定など）をガイド付きで入力可能。
    - 生成される .env テンプレートは .env を誤ってコミットしない旨のコメントを含む。
  - 設定検証ツール (kabusys.validate_config)
    - .env と config/*.yaml（存在する場合）の事前検証を実行。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML がある場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を読み、システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルトの合格閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - --from/--to/--db オプションをサポート。

- 実行／監視ランナー
  - Execution Engine 起動スクリプト (kabusys.run_execution)
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成（実運用時は実ブローカー、ペーパートレード時は MockBrokerClient）。
    - OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) により安全に停止。
    - PID ファイル管理（data/execution.pid をデフォルト）。
  - System Monitor 起動スクリプト (kabusys.run_monitoring)
    - 監視ループを起動し SystemMonitor.check_once() を定期実行。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（監視データは共通 DB に保存）。
    - 停止フラグ (data/stop_requested.flag) 検知による安全終了処理。

- ポートフォリオ構築関連 (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: スコア降順（同点時は signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重。全スコアが 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が上限 (max_sector_pct) を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバック 1.0）。
  - position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
      - risk_based: portfolio_value, risk_pct, stop_loss_pct を用いた理論株数算出。
      - equal/score: 重み（weights）に応じた配分。
      - lot_size（単元）で丸め、_max_per_stock による 1 銘柄上限を考慮。
      - aggregate cap（available_cash）を超過する場合はスケールダウンし、端数は残差大きい順に lot 単位で追加配分。
      - cost_buffer による保守的コスト見積りをサポート。
      - 価格情報が欠けている銘柄はスキップし、ログを出力。

- リサーチ / ファクター計算 (kabusys.research.factor_research)
  - DuckDB 接続を受けて prices_daily / raw_financials を参照し、モメンタム / ボラティリティ / 流動性などのファクターを計算する純関数群を提供。
  - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
  - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。NULL 伝播を正しく制御するための SQL を実装。
  - 長期窓やスキャン範囲は定数化され、ターゲット日からのスキャン期間を考慮した実装。

- ユーティリティ (kabusys.utils.process_priority)
  - プラットフォーム差異を吸収してプロセス優先度を設定するユーティリティを提供（Windows は HIGH_PRIORITY_CLASS 等、POSIX は nice 値を使用）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
  - psutil の権限不足や未サポート環境での例外を安全にハンドリングして警告出力。

- DB 初期化 / 互換性
  - monitoring 用テーブルを作成する init_monitoring_db が呼び出され、監視テーブルの存在を保証（冪等）。
  - sqlite3 と duckdb の両方の接続を使用する構成を採用。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- .env に秘密情報（API トークン等）を保存する点をウィザードで明示し、.env をリポジトリにコミットしないよう注意喚起を表示。

Notes / 注意事項
- .env の自動読み込みでは OS 環境変数が優先され、.env.local は .env を上書きします。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- run_monitoring は監視 DB に常に sqlite_path を使用します。環境に依らず監視データの保存先は本番用に想定されています。
- run_execution は paper_trading 環境で DB を分離するため、ペーパートレード時の実データ汚染を防ぎます。
- 一部の機能（config YAML の検証など）は外部ライブラリ（PyYAML）の有無に依存し、ない場合は該当チェックをスキップして警告を出します。

今後の予定（例）
- 個別銘柄ごとの lot_size を stocks マスタに持たせる拡張。
- position_sizing における価格欠損時のフォールバック（前日終値や取得原価の利用）。
- monitor の詳細なメトリクス収集やアラート送信機能の強化。