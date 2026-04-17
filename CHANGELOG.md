CHANGELOG
=========

すべての注目すべき変更点を記載します。  
このファイルは "Keep a Changelog" の形式に従っています。

Unreleased - 2026-04-17
-----------------------
- 追加 / 進行中
  - ai/news_nlp モジュールの処理フロー実装が途中（ソース末尾が切れているため、一部ロジックは未完）。完了時には OpenAI API 呼び出し周りの堅牢化・部分書き換え（DELETE/INSERT）の保護が有効になります。
- 修正予定 / 改善候補
  - price の欠損時のフォールバック価格（position_sizing / risk_adjustment の TODO）を導入し、エクスポージャーの過少評価を防ぐ。
  - tools や monitoring のログ/メトリクス出力の強化（監視ループや ExecutionEngine の停止挙動の更なる堅牢化）。

0.1.0 - 2026-04-01
------------------
注: 初回公開リリース。コードベースから推測される主要な機能群および実装上の重要点をまとめています。

Added
- 基本パッケージ
  - kabusys パッケージを導入。__version__ を 0.1.0 として公開。
  - パッケージの公開 API を __all__ で整理（portfolio / research / tools 等をエクスポート）。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を探索して決定。
  - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い）。
  - Settings クラスを導入し、アプリ各所から型安全に設定値を取得可能にした（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定 等）。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, MONITOR 関連環境変数など多数の設定を導入。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動エントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory により本番 / モックブローカーの切り替えをサポート。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をスレッドで実行、stop flag により安全停止。
    - リスクマネージャーにデフォルト設定を付与（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を利用して監視テーブルを初期化。
    - 停止フラグファイルによるループ終了、KeyboardInterrupt の取り扱い、例外時のログ出力を実装。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを run_execution/run_monitoring の起動時に行い、監視用テーブルが存在することを保証（冪等処理）。

- ユーティリティ
  - process_priority モジュールを追加（set_process_priority, set_cpu_affinity）。
    - Windows/Linux/Mac 等の差分を吸収してプロセス優先度（および CPU affinity）を設定するユーティリティを提供。
    - アクセス権限不足時や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: シグナルから候補選定（score 降順, signal_rank をタイブレーク）と等金額・スコア加重の重み計算を実装。スコア全0 の場合は等配分にフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: allocation_method（"risk_based", "equal", "score"）に基づいた株数算出ロジックを実装。lot（単元）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を用いた保守的見積り、残差処理による追加配分などをサポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新の財務レコードを銘柄ごとに取得）。
    - DuckDB を使用した SQL ベースの実装でパフォーマンスを重視。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン取得（複数ホライズンを1クエリで取得、入力検証あり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（欠損 / ties 対応、3 銘柄未満で None を返す）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを提供。
  - research パッケージは外部ライブラリに依存せず標準ライブラリ + duckdb で完結する設計。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を元に OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を付与し、ai_scores テーブルへ書き込む機能を実装（バッチ処理、トークン肥大化対策、スコアクリップ、429/ネットワーク/5xx に対するエクスポネンシャルバックオフ）。
  - ニュース取得ウィンドウを JST ベースで計算（前日 15:00 JST ～ 当日 08:30 JST を対象）。
  - 出力フォーマットの厳密な検証、部分失敗に備えた DB 更新戦略（影響を受けるコードのみ置換）を想定。

- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite を読み、期間指定で検証レポートを標準出力へ出力する CLI を追加。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等の指標算出、閾値に基づく PASS/FAIL 判定、P95 の計算実装。
    - DB テーブルが存在しない場合でも耐性を持つ（OperationalError のフォールバック）。

Changed
- 環境変数の読み込み挙動
  - OS 環境変数を保護する仕組みを導入（.env 読み込み時に OS 環境変数を上書きしない / .env.local は上書き可能だが OS 変数は保護）。
- DB 関連
  - 実行系と監視系で用途に応じた SQLite パスを切り分け（paper_trading 環境では paper_sqlite_path を使用）。

Fixed
- .env パーサーの改善により、引用符内のエスケープやインラインコメントの誤認識を修正。
- calc_score_weights: 全銘柄のスコアが 0 の場合は等金額配分にフォールバックして Warning を出すよう修正。

Security
- 各種秘匿情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）は Settings を通じて必須チェックを行う実装。未設定時は ValueError を送出して安全に失敗する。

Migration notes
- 環境変数:
  - KABUSYS_ENV: development | paper_trading | live のいずれかを指定。paper_trading を使うと発注関連がモック・DB 分離される。
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 DB を指定する場合はこちらを使用。
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。1 以上の整数を指定。無効値の場合はデフォルト 60 秒にフォールバック。
  - OPENAI_API_KEY: ai/news_nlp を利用する場合は必須。
- DB:
  - 監視用テーブルは run_* スクリプト起動時に自動的に初期化される（冪等）。
- 実行:
  - run_execution.py / run_monitoring.py は共にプロセス優先度を "high" に設定しようとします（権限がない場合は警告を出してスキップ）。

Notes / Known issues
- ai.news_nlp のソースが途中で切れているため、現状は完全実行できない箇所があります（Unreleased に記載）。本モジュールを本番運用する前に、レスポンスのパースと DB 書き込みの最終化部分を確認してください。
- position_sizing の price 欠損時のフォールバックロジックは未実装（TODO）。欠損株価があるとセクターエクスポージャーやポジション算出が過少評価される可能性があります。

ライセンスやセキュリティ通知などの追加的な変更は将来のリリースで追記予定です。