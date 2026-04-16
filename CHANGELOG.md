Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[0.1.0] - 2026-04-16
-------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をサブスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
    - PID ファイル出力用パスの利用（data/execution.pid デフォルト）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - 実行開始時にプロセス優先度を "high" に設定。
- 設定 / 環境変数管理
  - config.Settings クラスを提供。環境変数経由の設定取得をプロパティで実施。
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - .env パーサーは export プレフィックス、クォート文字列、インラインコメントに対応。無効行をスキップ。
  - 主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須チェックあり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL の検証
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等
    - PAPER_FILL_MODE（instant | partial | never | reject のバリデーション）
    - 監視しきい値（CPU/MEMORY/DISK）等のデフォルト値
- モジュール: portfolio
  - portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank の昇順を採用
    - calc_equal_weights: 等金額配分（1/N）
    - calc_score_weights: スコアに比例した重み。全スコアが 0 の場合は等配分にフォールバックして WARNING を出力
  - risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market regime に応じて投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 にフォールバック
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数算出。
    - risk_based: 損切り率・risk_pct を用いた単銘柄ベースの株数計算。
    - equal/score: ウェイトに基づく配分、per-position と aggregate の上限チェック、lot_size（デフォルト 100）で丸め。
    - 投資合計が available_cash を超えた場合はスケールダウンし、残余で端数を lot 単位で追加配分するロジックを実装。cost_buffer による保守的見積りをサポート。
- 監視関連
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化を保証（run_execution と run_monitoring で使用）。
- utils
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定。権限不足や未実装 API は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定（権限不足などは警告してスキップ）。引数検証あり。
- research
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。DuckDB の prices_daily を参照。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比の計算。NULL の伝播制御（true_range の計算）を明示。
    - calc_value: per / roe の計算。raw_financials テーブルの target_date 以前の最新レコードを取得。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターン算出（ホライズンは 1..252 の検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（<3 件）や分散ゼロは None を返す。
    - factor_summary / rank: 基本統計量・ランク関数を提供。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- tools
  - tools.paper_verification_report
    - Paper Trading の検証レポートを CLI 出力するスクリプトを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - オプション: --from / --to / --db。
    - 集計指標:
      - 稼働率（system_status）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下数（risk_logs）
      - レイテンシ（平均・最大・P95）
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - データ欠損に対しては N/A を表示し、OperationalError を想定してフォールバック。
- ai
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）で解析し、銘柄ごとに -1.0〜1.0 のスコアを ai_scores テーブルへ書き込むロジックを実装（バッチ処理・トリム・検証・再試行付き）。
    - バッチサイズ、最大トークン対策、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - 出力 JSON の厳密なバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（影響範囲を限定して DELETE→INSERT）を設計方針として明記。
    - calc_news_window ユーティリティでニュース収集ウィンドウ（JST基準）を計算。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キー等の機密情報は環境変数経由で取得する設計。未設定時は明示的な例外を発生させる箇所あり（ai.news_nlp など）。

Notes / 非機能的事項
- DuckDB / SQLite に依存するモジュール群は、対象テーブル（prices_daily / raw_financials / raw_news / trade_logs / system_status / risk_logs / ai_scores など）が存在することを前提とした実装になっています。テーブルが存在しない場合は OperationalError を捕捉してフォールバックする処理を一部で行っていますが、実運用前にスキーマの準備が必要です。
- run_* スクリプトはプロセス優先度設定や停止フラグ検知など運用向けの振る舞いを備えています。コンテナや限定ユーザー権限環境では優先度 / affinity の設定が失敗する可能性があるため、該当場面では警告ログでスキップされます。
- 一部関数は将来の拡張（銘柄ごとの lot_size 搭載、価格フォールバック等）をコメントで示しています。

未収録事項（今後検討）
- エンドツーエンドの統合テスト、CI 用の設定、テーブル作成用マイグレーションスクリプトは現状含まれていません。運用前にはこれらの準備を推奨します。