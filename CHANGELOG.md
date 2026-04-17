Changelog
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はこのコードスナップショットの作成日 (2026-04-17) を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: kabusys パッケージを追加（__version__ = 0.1.0）。
- 設定管理:
  - kabusys.config.Settings クラスを追加。環境変数と .env(.env.local) の自動読み込み、保護された OS 環境変数扱い、各種設定プロパティ（DB パス、PID ファイル、閾値、環境モード判定など）を提供。
  - .env パーサを独自実装（コメント／クォート／export 形式対応）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 各種入力値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）と未設定時の例外処理を実装。
- 実行/監視用エントリスクリプト:
  - run_execution.py を追加。ExecutionEngine 起動スクリプトを提供。
    - プロセス優先度を起動時に High に設定。
    - paper_trading モードでは専用の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視 (data/stop_requested.flag) を実装。
    - デフォルトのリスク設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を Execution 起動時に設定。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知、例外発生時のロギングと継続、プロセス優先度設定などを実装。
- 監視 DB 初期化:
  - kabusys.monitoring.monitoring_db:init_monitoring_db を呼んで監視テーブルの存在を保証する処理を各起動スクリプトに組み込み（冪等）。
- ポートフォリオ構築（純粋関数群）:
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選別。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアがゼロの場合は等金額にフォールバックして WARNING）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックにより候補を除外する関数（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 にフォールバックして警告。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: 複数の配分方式（"risk_based", "equal", "score"）をサポート。単元株（lot_size）への丸め、個別上限・集計上限（available_cash）でのスケールダウンアルゴリズム、残差処理による追加配分ロジックを実装。
    - 手数料/スリッページ見積り用の cost_buffer パラメータをサポート。
    - ポートフォリオ計算はメモリ内の純粋関数として設計（DB 参照なし）。
- リサーチ（ファクター計算・解析）:
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクターを算出（MA200、ATR20、リターン等）。
  - kabusys.research.feature_exploration:
    - calc_forward_returns, calc_ic（スピアマンのランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ __all__ を整備。
- ユーティリティ:
  - kabusys.utils.process_priority:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows と POSIX (Linux/Darwin/FreeBSD) を抽象化し psutil を利用して優先度 / CPU affinity を設定。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ツール:
  - kabusys.tools.paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出して標準出力へ整形表示。日付フィルタ機能（--from/--to）あり。DB のテーブルが存在しない場合は N/A を扱う耐性を実装。
- AI ニュース NLP（ニュースセンチメント）:
  - kabusys.ai.news_nlp:
    - ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む設計と実装（定数、ウィンドウ計算 calc_news_window、score_news の骨格、API リトライ方針、バッチ処理設計、JSON 出力フォーマット制約等）。429/ネットワーク/5xx に対する指数バックオフやレスポンスバリデーション、スコアの ±1.0 クリップ、部分置換（DELETE+INSERT）による部分失敗耐性などを考慮。
- DB: DuckDB/SQLite を併用する設計（duckdb は価格データ等の分析向け、sqlite は監視/発注ログ等の永続化向け）。

Changed
- 該当なし（初期リリース）。

Fixed
- 該当なし（初期リリース）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

注意点 / 既知の制約・TODO
- ai/news_nlp.score_news の実装はこのスナップショットで途中（ソースの最後が切れている）であり、記事取得集約部分の完遂や全体の結合テストが必要です。API キーの未設定時は例外を送出する設計になっています。
- position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価をフォールバックする案が示唆されています。
  - 現在は lot_size を全銘柄共通で使用。将来的には銘柄別 lot_map を受け取る拡張予定（TODO コメントあり）。
- DuckDB / SQLite のテーブル存在に依存する箇所が多く、実行前に必要なテーブル作成 / データ投入が必要です。tools/paper_verification_report はテーブルが無い場合に OperationalError をキャッチして耐性を持たせていますが、本番的運用では事前準備が推奨されます。
- process_priority / cpu_affinity の設定は権限や OS に依存するため、設定に失敗した場合は警告を出してスキップする安全設計になっています。
- run_monitoring は「監視は常に本番 sqlite_path を使う」仕様になっているため、paper_trading 環境で監視を分離したい場合は注意が必要です。

貢献者
- このスナップショットに含まれるコードの作成者（コミット履歴がないため省略）。README / CONTRIBUTING 等は未追加。