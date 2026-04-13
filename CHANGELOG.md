CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更（現状なし）
- 各リリース: 日付付きで追加・変更・修正点を列挙

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 基本パッケージ初期リリースを追加。パッケージメタ情報として kabusys.__version__ = "0.1.0" を設定。
- 実行用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB に接続し、monitoring テーブルを初期化。
    - DuckDB 接続を併用。
    - check_once() 実行中の例外を捕捉してログ出力しループ継続（堅牢化）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository・OrderManager・RiskManager・Reconciler 等を組み立てて ExecutionEngine.run_session を実行。
    - 起動時にプロセス優先度を "high" に設定。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown 等）を提供。

- 設定管理
  - kabusys.config
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入し、環境変数をプロパティ経由で安全に取得（各種既定値・バリデーションを含む）。
    - 各種設定プロパティを追加:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）、PAPER_TRADING_SQLITE_PATH
      - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK の閾値
      - ログレベルと環境（KABUSYS_ENV の validation: development / paper_trading / live）
    - settings インスタンスをモジュール変数として公開。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアで重み付け。全スコアが 0 の場合は等金額配分へフォールバックして WARNING を出力。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 同一セクター集中上限を評価し、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じて投下資金乗数を返す（bull/neutral/bear + フォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap スケーリング実装。

- 研究 / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB に直接問い合わせる SQL を用いた高速実装。
    - 各種窓幅・スキャン範囲の定数化（例: MA200, ATR20 等）。
  - kabusys.research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマンランク相関）、rank（平均ランクによる同順位処理）、factor_summary（基本統計量）を実装。
    - Pandas 等に依存しない純 Python 実装。

- AI ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）に送って銘柄ごとの sentiment（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事トリム（最大記事数／文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ、JSON レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - calc_news_window ユーティリティ（JST ベースの集計ウィンドウ）を提供。
    - API キー未設定時は ValueError を送出。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、PASS/FAIL 判定を出力（閾値はソース内定義）。
    - コマンドラインオプションで期間指定 (--from / --to) と DB パス (--db) を受け取る。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level) を実装し、Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収。アクセス権限のない場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピニング機能を実装（権限エラー時は警告）。

Changed
- 初期実装のため、多くの機能が新規追加（上記参照）。
- run_monitoring および run_execution の起動シーケンスはプロセス優先度設定 → 設定読み込み → DB 初期化 → コンポーネント初期化 → メイン処理 という順序で明示化。
- .env の読み込み順序は OS 環境変数 > .env.local > .env（.env.local が優先で上書き）とし、既存の OS 環境変数は protected として上書きされない挙動を採用。

Fixed
- 環境変数値の堅牢化・バリデーションを追加:
  - MONITOR_POLL_INTERVAL が非整数または 0 以下の場合に警告を出しデフォルトへフォールバック。
  - PAPER_FILL_MODE と KABUSYS_ENV、LOG_LEVEL の許容値チェックを実装し、不正値で ValueError を投げる。
  - Settings._require() により必須環境変数未設定時に明示的なエラーを出力。
- 各種 DB クエリ部で sqlite3.OperationalError を考慮したフォールバックを導入（paper_verification_report など）。
- run_monitoring のポーリングループで check_once() 内の例外を捕捉し、ループ継続することで監視エージェントの安定性を向上。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を用いる。未設定時は明示的にエラーを投げることで誤使用を防止。

Notes / Known limitations
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応への拡張を検討）。
- apply_sector_cap は price_map に価格データが欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり。
- news_nlp の処理は API コスト・レイテンシに依存するため、本番運用ではレート管理やコスト上限の追加検討が必要。
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials 等）に依存。テーブルが存在しない場合は結果が空や None になる点に注意。

License
- 本リリースのライセンス情報はリポジトリのライセンスファイルを参照してください。