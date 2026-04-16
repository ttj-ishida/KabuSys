CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
日付はリリース日または変更判明日を示します。

Unreleased
----------

- なし

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース: KabuSys の基本機能群を追加。
- パッケージ全体
  - パッケージバージョンを設定: __version__ = "0.1.0"。
  - 主要サブパッケージ: data, strategy, execution, monitoring, portfolio, research, ai, tools, utils を公開。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を利用して実ブローカー／モックを切り替え。
    - エンジンは別スレッドで実行、data/stop_requested.flag を検知して安全に停止。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境に関わらず本番 sqlite_path を使用して監視テーブルを管理。
    - 停止フラグ (data/stop_requested.flag) を検知してループ終了。

- 設定・環境変数管理
  - config.Settings クラスを追加し、環境変数から各種設定を取得する API を提供。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で判定）。
  - .env/.env.local の読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き許可）。
  - 読み込み時に OS 環境変数を保護する protected キーセットを採用。
  - .env パースロジックを強化: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理。
  - 各種設定プロパティを実装（DB パス、PID/kill フラグパス、閾値、env/log level 検証、paper_fill_mode の検証など）。

- Execution / Risk / Order コンポーネント（基盤）
  - ExecutionEngine 起動に必要なコンポーネントを組み立てる初期実装を追加（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
  - RiskManager にデフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
  - ExecutionEngine は pid ファイルを管理し、停止フラグ検知で stop() を呼ぶ機構を持つ。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度設定（Windows / POSIX を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") を提供。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加（指定なしは設定しない）。権限不足や未対応環境は警告でスキップ。
  - utils パッケージの基本構造を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates(buy_signals, max_positions) : スコア降順 + signal_rank による候補選定。
    - calc_equal_weights / calc_score_weights : 等金額配分、スコア加重配分（スコア全体が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap : セクター集中を防ぐため既存ポジション比率を計算し、新規候補を除外。
    - calc_regime_multiplier : market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes : weight/候補/利用可能現金等から銘柄ごとの発注株数を計算。risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap によるスケールダウンと残差処理を実装。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value : DuckDB 上の prices_daily / raw_financials を参照して各種ファクターを計算。
    - 各関数はデータ不足時に None を返すなど堅牢な振る舞い。
  - research.feature_exploration
    - calc_forward_returns : n 日後の将来リターンを計算（複数ホライズン対応、入力バリデーションあり）。
    - calc_ic : スピアマンのランク相関（IC）計算（同順位の平均ランク処理を含む）。
    - rank / factor_summary : ランク変換、基本統計量算出（count/mean/std/min/max/median）。
  - research パッケージは外部依存を最小化（標準ライブラリ + duckdb）する設計。

- AI ニュース NLP（実験的）
  - ai.news_nlp
    - raw_news / news_symbols の集約から OpenAI API へバッチ送信して銘柄ごとのセンチメント ai_score を生成し ai_scores テーブルに書き込む処理を実装（gpt-4o-mini を想定）。
    - 処理上の主要機能: バッチ (_BATCH_SIZE=20)、最大トークン肥大化対策、文字数/記事数のトリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 へのクリップ、部分失敗を想定した DB 上書き戦略。
    - OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。
    - SQLite（paper_trading.db）から集計して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを表示。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - --from/--to/--db オプションをサポート。DB が無ければエラーメッセージを表示。

Changed
- .env 読み込みの既定動作
  - 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート探索は __file__ を起点に親ディレクトリを上方向に探索（CWD に依存しない挙動）。

Fixed
- .env パーサーの改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善し現実的な .env 記述に対応。
- ファクター / リサーチ集計クエリ
  - DuckDB 上でのウィンドウ関数・NULL 伝播を考慮し、true_range 計算や移動平均の欠損処理を明示的に扱うよう修正。

Security
- OpenAI API キーの扱い
  - ai.news_nlp は API キーを必須とし、外部環境変数または引数で明示的に渡すことを要求。キーの自動公開を避ける設計。

Notes / Known limitations
- ai.news_nlp は大量記事処理・API 呼び出しのため実行環境の API レートやコストに注意が必要です（実運用時はキー管理・レート制御の追加検討を推奨）。
- position_sizing の lot_size は現状グローバルで固定（将来的に銘柄別 lot_map に拡張予定、TODO コメントあり）。
- 一部の振る舞いは現状想定に依存（例: price が欠落した場合の exposure の過少見積り等）。コード内に TODO を挿入しており将来改善を予定。

今後の予定 (非 exhaustive)
- AI モジュールの堅牢化（部分失敗リトライ策略の改善、ログ・監査の強化）
- 銘柄別単元株情報の導入と position_sizing の拡張
- モニタリングアラート (LINE 等) の実装と自動通知フローの追加
- テストカバレッジの強化（特に DuckDB クエリとリサーチ関数）

-----