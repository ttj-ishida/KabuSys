CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.

## [0.1.0] - 2026-04-16 (Initial release)

Added
-----
- 全体
  - 初期リリース。システムの自動売買、監視、リサーチ、ポートフォリオ構築、ツール群、ユーティリティを含む基盤を実装。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV = paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - Engine はバックグラウンドスレッドで run_session を実行。data/stop_requested.flag の検知で安全に停止。
    - 起動時に PID ファイル path（data/execution.pid デフォルト）を使用。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値は broker.get_available_cash() を利用して設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを書き込む設計。
    - data/stop_requested.flag による停止検知を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority を利用）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーを実装:
      - export KEY=val 形式対応、クォート付き値（単一／二重）とバックスラッシュエスケープに対応。
      - コメント処理、無効行スキップ、上書き制御（override / protected）をサポート。
    - Settings クラスを追加し、各種環境変数の検証とラップを提供:
      - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
      - PAPER_FILL_MODE の検証（instant|partial|never|reject）
      - 監視閾値・ファイルパス・環境種別（KABUSYS_ENV）の検証ロジック
      - ログレベル検証
    - settings インスタンスをモジュールレベルで公開。

- 監視 / モニタリング
  - monitoring_db 初期化呼び出しを run_execution/run_monitoring に組み込み、監視テーブルの存在を冪等に保証。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定と重み付けロジックを提供:
      - select_candidates: スコア降順・タイブレークは signal_rank 昇順で上位 N を選択。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0.0 の場合は等配分へフォールバックして WARNING）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジックを実装。既存ポジションからセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes を実装:
      - allocation_method: "risk_based"（許容リスク×stop_loss を基に算出）と "equal"/"score" をサポート。
      - lot_size（単元）を考慮した丸め処理。
      - per-stock 上限（max_position_pct）と aggregate cap（available_cash）を考慮し、必要に応じてスケーリング。
      - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積もりと、スケールダウン後の残余キャッシュを利用した追加配分（remainders）を実装。
      - 価格欠損時のスキップ、0 以下価格の扱い、ログ出力によるデバッグ情報。

- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離 (ma200_dev) を DuckDB (prices_daily) から計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に制御。
    - calc_value: raw_financials と prices_daily を組み合わせ、PER（EPS 不在・ゼロは None）と ROE を算出。target_date 以前の最新財務データを銘柄毎に取得。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで取得。horizons の検証を実施。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足や同順位処理に対応。
    - rank, factor_summary: ランク付け（同順位は平均ランク）とファクター列の基本統計量（count/mean/std/min/max/median）を提供。
    - すべて標準ライブラリ・DuckDB のみで完結する設計（pandas 等に依存しない）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news、news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装（意図）。
    - 処理方針:
      - 対象ウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB で比較）。calc_news_window を提供。
      - 銘柄ごとに記事数・文字数の上限を設定（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）してトークン肥大化を抑制。
      - 最大バッチサイズ 20 銘柄で API に送信、JSON Mode 出力を期待。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（上限あり）。
      - レスポンス検証、スコアを ±1.0 にクリップ。
      - 部分失敗に備え、更新は対象コード絞り込みで DELETE→INSERT 方式（既存スコア保護）で実行する方針。
    - OpenAI API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - CLI で --from / --to / --db を指定可能（デフォルト DB は data/paper_trading.db）。
    - システム稼働率（system_status）、注文成功率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（latency, P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 の独自実装、DB のテーブル未存在時に安全に N/A を扱う耐障害性を実装。
    - 出力は標準出力への整形されたレポート。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX を吸収）。
    - set_cpu_affinity(cpu_count) を実装（第一 N コアに固定、存在しないコア数は全コア使用として処理）。
    - 権限不足や未対応 OS の場合は警告を出しスキップするフェイルセーフ。
    - Windows 固有の HIGH_PRIORITY_CLASS 等や POSIX の nice 値をマッピング。

Changed
-------
- なし（初回リリースのため該当なし）。

Fixed
-----
- なし（初回リリースのため該当なし）。

Security
--------
- 環境変数の自動ロードで OS 環境変数を保護するため protected セットを導入（.env ファイル上書き時の安全策）。

Notes / Usage tips
------------------
- 環境変数関連
  - .env 自動読み込みはデフォルトで有効。テストや特殊な環境で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須の機密情報（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings を通じて取得するため、未設定時は起動時に例外が発生します。.env.example を参照してください。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を秒で設定できます。不正な値はデフォルト 60 秒にフォールバックします。

- Paper Trading
  - paper_trading 環境では実取引 API ではなく MockBrokerClient を使用する想定（BrokerClientFactory にて選択）。
  - paper_trading 用 DB は default data/paper_trading.db を使用し、本番監視 DB と完全に分離。

- OpenAI
  - ai/news_nlp は OpenAI API キーが必要。API 利用時のレート制限やコスト、出力フォーマットの保証に注意してください。

Breaking Changes
----------------
- なし（初回リリース）。

Acknowledgements / References
-----------------------------
- 設計ドキュメント参照: PortfolioConstruction.md, StrategyModel.md（コード内コメントに言及あり）。
- DuckDB を利用したローカル分析・ファクター計算に最適化。

(この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリース方針に応じて適宜修正してください。)