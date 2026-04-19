Keep a Changelog 形式に準拠した CHANGELOG.md（日本語）
以下は提示されたコードベースから推測して作成した変更履歴です。実装の注釈や既知の制約（TODO／未実装箇所）も併記しています。

Unreleased
---------
- Added
  - なし（次回リリースに向けた未実装/改善項目を以下の「注記」に記載）
- Changed
  - なし
- Fixed
  - なし
- Notes / TODO
  - research/factor_research.calc_momentum の実装が途中で終了している（ファイル末尾が切れているため補完が必要）。
  - position_sizing: 銘柄ごとの単元（lot_size）を将来的に銘柄マスタから取得する拡張がコメントで示されている（未対応）。
  - risk_adjustment.apply_sector_cap: price の欠損時フォールバックの扱いに関する TODO コメントあり（前日終値等のフォールバック実装が望ましい）。

0.1.0 - 2026-04-19
-----------------
Added
- 全体
  - 初期バージョンのパッケージ追加。パッケージバージョンは __version__ = "0.1.0"。
  - DuckDB と SQLite を併用する設計（分析用に DuckDB、監視・履歴は SQLite）。
  - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env のパースロジックを強化（export プレフィックス対応、クォート内エスケープ処理、インラインコメントの取り扱い等）。
  - .env 生成/更新用の対話式ウィザード（kabusys.config_setup）。
  - 起動前設定チェック用 CLI（kabusys.validate_config）。--strict モードをサポートし、警告を失敗扱いにできる。
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）。
    - stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、失敗時のフォールバック（標準出力のみ）。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プロセス優先度／CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応、psutil を利用。
    - set_process_priority, set_cpu_affinity を提供。アクセス権限不足時は警告でスキップ。
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト。
      - 起動時にプロセス優先度を high に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離（Mock ブローカークライアントを想定）。
      - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の利用。
      - ExecutionEngine を別スレッドで実行し、停止フラグ検出で engine.stop() を呼ぶ。
    - run_monitoring.py: SystemMonitor 起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データの単一ソース化）。
      - 停止フラグ（data/stop_requested.flag）検出でループを終了。
  - Execution 関連
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は Mock を返す設計想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine 等の組み立て。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - Monitoring / Tools
    - 監視 DB の初期化ユーティリティ（monitoring_db.init_monitoring_db）を起動前に呼び冪等に存在を保証。
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを実装。
      - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定。
      - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
      - 日付フィルタ（--from / --to）対応、DB パスは引数または環境変数で指定可能。
  - Portfolio（ポートフォリオ構築関係）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順・タイブレークに signal_rank を使用。上位 N 件を選択。
      - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等重配分にフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限。既存保有のセクター別エクスポージャ算出により当該セクターの新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは警告を出して 1.0 にフォールバック。
      - risk_adjustment にて price 欠損時のフォールバックは TODO コメントあり。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づいて銘柄ごとの発注株数を決定。
      - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）・aggregate cap（available_cash）を考慮。
      - コストバッファ（cost_buffer）を考慮した保守的見積りとスケーリングロジック実装。
      - aggregate cap 超過時のスケールダウンと残差処理アルゴリズムを実装（残差の大きい順に lot_size 単位で追加配分）。
- Changed
  - なし（初期公開）
- Fixed
  - なし（初期公開）
- Security
  - 環境変数や .env に関する扱いの説明を README/ウィザード内で強調（.env を絶対に Git に含めない旨の注記あり）。
- Notes / Known limitations
  - research/factor_research モジュールはファクター計算を想定（momentum, value, volatility, liquidity）だが、calc_momentum の定義が途中で終端しており完全実装が必要。
  - .env 自動読み込みはデフォルトで有効。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
  - run_monitoring は環境にかかわらず「監視用 DB」に本番 sqlite_path を使う設計。意図的な分離や文書化に注意。
  - process_priority / set_cpu_affinity は権限不足や未サポート OS の場合にスキップして安全にフォールバックする設計。
  - Paper Trading の振る舞い（MockBroker の細部、fill_mode の挙動）は設定（PAPER_FILL_MODE）により変化。許容値チェックを実装済み（instant/partial/never/reject）。

参考: 主な環境変数（コードより抽出）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア有無を制御）

作業推奨（次回リリース候補）
- research/factor_research.calc_momentum の完成（および他ファクターの単体テスト追加）。
- position_sizing の銘柄別 lot_size サポート実装。
- apply_sector_cap の price 欠損時フォールバック（前日終値等）実装。
- BrokerClientFactory の MockBroker 実装詳細の文書化・テスト追加。
- CI で validate_config や paper_verification_report を用いた回帰チェックを追加。

もし CHANGELOG に日付や細かいコミット単位の履歴（例: 直近の修正やバグフィックス）を反映したい場合は、追加のコミット履歴や目的の差分（どのファイルをどのように変更したか）を教えてください。それに基づいてより正確な履歴を作成します。