CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。

Unreleased
----------

- （現時点のコードベースは初期リリース相当のまとまった実装です。今後の変更はここに追記されます）

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用する仕組みを導入（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。PID ファイルへ書き込み（data/execution.pid）。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - プロセス優先度を起動時に "high" に設定。
- 設定 / 環境変数ユーティリティ
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装し、export KEY=val 形式、単一/二重クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定値をラップ（DB パス、API トークン、しきい値、環境判定プロパティなど）。
    - 設定値バリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
- データ処理 / ポートフォリオ構築
  - portfolio パッケージを実装（純粋関数群）
    - portfolio_builder.py
      - select_candidates: スコア順に候補選定（タイブレークロジックあり）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限。既存保有からセクター露出を算出し、上限超過セクターの新規候補を除外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した発注株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリング（cost_buffer を考慮）を実装。
      - risk_based では stop_loss_pct を用いたポジションサイズ算出。aggregate cap 超過時はスケールダウン後に残余キャッシュで優先度に応じた lot 単位で再配分するロジックを実装。
- 監視 / DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db（起動時に監視テーブルが存在することを保証。冪等処理）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を実装。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - CLI 引数 --from/--to/--db に対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
    - P95 計算、日付フィルタ、テーブルの存在チェックや OperationalError 耐性を実装。
- リサーチ / ファクター計算
  - research パッケージ（DuckDB 接続ベース）を実装
    - factor_research.calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照して各種ファクター（mom_1m/3m/6m, MA200乖離, ATR20, avg_turnover, PER, ROE 等）を計算。
    - feature_exploration.calc_forward_returns: 将来リターン（任意ホライズン）を計算。horizons の妥当性チェックあり。
    - feature_exploration.calc_ic / rank / factor_summary: スピアマン IC、ランク付け（平均ランクで ties 処理）、ファクター統計サマリを実装。
    - すべて外部 API に依存せず DuckDB と標準ライブラリのみで動作する設計。
- AI ニュース処理（初期実装）
  - ai/news_nlp.py
    - raw_news を元に OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を実装（バッチ送信、リトライ、スコアクリップ、結果バリデーション、ai_scores テーブル書き込み方針など）。
    - ニュース収集ウィンドウ計算（JST ベース）を実装。
    - API キー未設定時に ValueError を発生させる安全策を導入。
    - フェイルセーフ設計（API 失敗時はスキップして継続）、トークン肥大化対策（記事数/文字数制限）を実装。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows と POSIX 系（Linux / Darwin / FreeBSD）に対応する nice/priority 設定を吸収し、未対応 OS や権限不足時は警告を出してスキップする堅牢設計。
    - 呼び出し元はプラットフォームを意識せずに優先度設定可能。
- パッケージエクスポート
  - kabusys.__init__.py: __version__ = "0.1.0"、公開 API (__all__) を定義。

Changed
- （初期リリースのため "Changed" に記載する過去履歴はありません）

Fixed
- .env ファイルのパースの堅牢化
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、クォートなし値のインラインコメント解釈（直前が空白/タブの場合のみ）などを実装し、実運用での .env 設定ミスに耐性を持たせた。

Deprecated
- （このリリースではなし）

Removed
- （このリリースではなし）

Security
- 必須環境変数に対して明示的にエラーを投げるように実装
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で未設定時に ValueError を送出。
  - OpenAI API を使う機能は OPENAI_API_KEY または明示的引数が未設定の場合にエラーとする（安全策）。

Notes / Upgrade / Migration
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を調整可能（整数秒、1 以上）。不正値はデフォルト 60 秒にフォールバック。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テストや CI 向け）。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれか。無効な値を設定すると例外が発生するため注意。
- paper_trading 用 DB はデフォルトで data/paper_trading.db。既存の paper_trading データと本番 monitoring DB（data/monitoring.db）は分離される。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）を使って外部から安全に停止できる。
- DuckDB / SQLite を併用する設計になっているため、DuckDB のファイルパス（DUCKDB_PATH）や SQLite パス（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）の設定に注意してください。
- ai/news_nlp の処理は API 呼び出しを伴うためコスト・レート制限に注意。未処理のエッジケースや部分失敗時の DB 保護（部分更新）設計は導入済み。

Known limitations / TODO
- ai/news_nlp.py は大枠の設計・処理（バッチング、リトライ、バリデーション）を実装しているが、実運用上の細かいエラー処理やログ出力のチューニングが今後必要になる可能性があります。
- position_sizing.calc_position_sizes:
  - price 欠損（0.0）の場合にエクスポージャーや上限が過少見積りになる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討中（コメントで TODO を記載）。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後の環境でルートが検出できない場合は自動ロードをスキップします（その場合は環境変数を明示設定してください）。

問い合わせ / 貢献
- このリポジトリに関する質問、バグ報告、改善提案は issue を作成してください。コード内の docstring とコメントに実装意図を記載していますので参照ください。