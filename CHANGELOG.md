CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

フォーマットの慣例:
- 変更は分類（Added, Changed, Fixed, ...）ごとに整理しています。
- 日付はリリース日を示します。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース: KabuSys のコア機能群を追加しました。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
  - 設定管理
    - kabusys.config.Settings: 環境変数/.env による設定読み込みを提供。
    - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込み。OS 環境変数の上書きを防ぐ保護機構あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env のパース強化: export 形式、クォート内エスケープ、インラインコメントの取り扱いなど。
    - Settings に多数のプロパティを実装（J-Quants / kabuステーション / LINE / DB パス / Paper Trading 用設定 / 監視閾値 / 環境・ログレベル検証 等）。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証ロジックを追加。

  - 実行エントリスクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - プロセス優先度を "high" に設定（psutil 経由、プラットフォーム差分吸収）。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite(DB: PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、本番 DB と完全分離。
      - 監視テーブルの初期化（init_monitoring_db を冪等に呼び出し）。
      - DuckDB 接続を使用（prices_raw 等の分析用）。
      - Broker クライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() による実行開始。
      - RiskManager のデフォルト設定値を明示（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker.get_available_cash() から取得。

    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
      - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用（監視データは本番 DB を想定）。
      - プロセス優先度を "high" に設定。
      - SQLite / DuckDB 接続、SystemMonitor.check_once() のループ処理、例外捕捉・ログ出力、KeyboardInterrupt による優雅な終了処理。

  - モジュール: portfolio
    - 銘柄選定 / 重み計算:
      - select_candidates: スコア降順・同点は signal_rank 昇順で上位 N を返す。
      - calc_equal_weights: 等金額配分（1/N）。
      - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
    - リスク調整:
      - apply_sector_cap: セクター集中制限。既存保有を考慮して同一セクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数。bull=1.0, neutral=0.7, bear=0.3。未知のレジームは 1.0 でフォールバック。
    - ポジションサイズ決定:
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数計算。lot_size による丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer による保守計上、端数処理のための残差分配ロジックなどを実装。
      - price 欠損に対するデバッグログと TODO（将来的に前日終値等のフォールバックを検討）。

  - 研究（research）モジュール
    - factor_research:
      - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算を実装。データ不足時は None を返す扱いに。
      - 固定パラメータ（MA200, ATR20 等）とスキャン範囲の定義。
    - feature_exploration:
      - calc_forward_returns: 将来リターン（fwd_1d, fwd_5d, fwd_21d など）を計算。horizons のバリデーションあり。
      - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。3 レコード未満は None を返す。
      - rank / factor_summary: ランク変換・基本統計量計算（count/mean/std/min/max/median）を提供。
    - research パッケージの __all__ エクスポートを整備（zscore_normalize を含む）。

  - AI / ニュース処理
    - kabusys.ai.news_nlp:
      - raw_news / news_symbols から銘柄ごとに記事を集約し OpenAI API (gpt-4o-mini) を用いてセンチメントを -1.0〜1.0 でスコアリング。
      - スコアは ±1.0 にクリップ。
      - バッチ処理（最大 20 銘柄/コール）、1 銘柄当たりの記事数・文字数上限（記事数最大 10、文字数最大 3000）を設定してトークン増大を抑制。
      - 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ（上限回数あり）。
      - 出力検証（JSON 形式、期待するキーと型の検査）後に ai_scores テーブルへ置換的に書き込み（部分失敗時に既存スコアを保護）。
      - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

  - ツール
    - tools.paper_verification_report:
      - Paper Trading 用 SQLite(DB) から統計を集計し検証レポートを標準出力に表示する CLI を追加。
      - 判定基準（稼働率/注文成功率/送信率/P95 レイテンシ）を定義し PASS/FAIL を出力。
      - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

  - ユーティリティ
    - kabusys.utils.process_priority:
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX に対応。権限不足等は警告してスキップ。
    - duckdb と sqlite3 両方を接続先として利用する設計を導入。

  - 依存ライブラリ（利用想定）
    - duckdb: データ分析用
    - psutil: プロセス優先度 / CPU affinity
    - openai: ニュース NLP（OpenAI）クライアント

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / Migration
- DB 分離:
  - paper_trading 環境では paper_sqlite_path (デフォルト: data/paper_trading.db) を使用し、本番 sqlite_path(data/monitoring.db) と分離します。既存運用環境から移行する場合は PAPER_TRADING_SQLITE_PATH を適切に設定してください。
  - 監視(run_monitoring) は明示的に本番 sqlite_path を使用する設計です（監視データの配置に注意してください）。
- 環境変数:
  - 重要: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須（Settings にて未設定で ValueError を送出）。
  - OPENAI_API_KEY は ai.news_nlp を利用する際に必要。
  - MONITOR_POLL_INTERVAL は監視ポーリング秒数（整数、1 以上）。
  - PAPER_FILL_MODE の値は instant / partial / never / reject のいずれかである必要があります。
  - KABUSYS_ENV: 有効値は development / paper_trading / live。
  - KILL_FLAG_* / PID_FILE_PATH 等の監視関連パスと閾値（CPU/MEMORY/DISK）は Settings で環境変数から設定可能。
- 実行時権限:
  - プロセス優先度や CPU affinity の設定は OS と実行ユーザの権限に依存します。権限不足時は警告ログを出してスキップします。
- エラー耐性:
  - run_monitoring のループ内では check_once() の例外を捕捉してログ出力し、次回ポーリングまで待機して継続します。
  - ai.news_nlp は API エラー時も失敗を局所化して可能な限り継続する設計です（フェイルセーフ）。
- TODO / 既知の制約:
  - portfolio.position_sizing: price 欠損時のフォールバック価格（前日終値や取得原価）については将来的な拡張を想定しています（現在はログ出力してスキップするのみ）。
  - duckdb の executemany の制約により、空パラメータ群は事前にチェックしてスキップする必要があります（ai モジュール等で言及あり）。
  - research モジュールは DuckDB のテーブル構成（prices_daily / raw_financials 等）に依存します。データ整備が前提です。

セキュリティ
- OpenAI API キーや各種トークンは環境変数で管理してください。設定ミスによる漏洩に注意してください。

ライセンス
- （ソースにライセンス表記が無いため、配布時には適切なライセンスを付与してください）

--- 

補足:
- この CHANGELOG は提示されたコードベースの内容から推測して作成した初期リリース記述です。実際のリリース履歴や日付・内容は運用方針に応じて調整してください。