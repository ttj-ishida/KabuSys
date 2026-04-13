# Changelog

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

追記: この CHANGELOG は、与えられたコードベースの内容から推測して作成したものです。実際のコミット履歴とは一致しない場合があります。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ初回実装:
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループを開始する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックし、警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用して DB に接続。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理:
  - kabusys.config.Settings を実装:
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml に基づく）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数読み込みのパーサ（export 形式、クォート・エスケープ・インラインコメント対応）。
    - 各種環境変数プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY ではなく別箇所参照だが必須キーは _require() によって検証される）。
    - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db, PID_FILE_PATH=data/execution.pid, KILL_FLAG_PATH=data/kill.flag。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - 環境種別検証（development, paper_trading, live）およびログレベル検証。
- 監視 DB 初期化:
  - init_monitoring_db を使用して監視用テーブルの存在を保証（冪等処理）。
- ユーティリティ:
  - utils.process_priority.set_process_priority: psutil を用いて Windows / POSIX（Linux, Darwin, FreeBSD）でプロセス優先度を設定するユーティリティを追加。失敗時は警告を出してスキップ。
  - utils.process_priority.set_cpu_affinity: カレントプロセスの CPU affinity を設定する関数を追加（cpu_count=None なら設定しない）。
- ポートフォリオ構築関連モジュール:
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順・タイブレークルール実装）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中制限。既存保有をセクター別に評価し上限超過セクターの新規候補を除外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear）
  - portfolio.position_sizing:
    - calc_position_sizes（リスクベース / equal / score 配分に対応。lot_size 単位で丸め、aggregate cap と cost_buffer を考慮したスケーリングと再配分ロジックを実装）
- 研究（Research）モジュール:
  - research.factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）
    - calc_value（EPS ベースの PER、ROE）
    - DuckDB を使った SQL ベースの実装（prices_daily / raw_financials テーブル参照）
  - research.feature_exploration:
    - calc_forward_returns（将来リターン計算、horizons の検証）
    - calc_ic（スピアマンランク相関による IC 計算、十分なレコード数がない場合は None）
    - factor_summary（各カラムの count/mean/std/min/max/median）
    - rank（同順位は平均ランク）
  - research パッケージ __all__ に主要関数を公開（zscore_normalize は data.stats から輸入）
- ツール:
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加。コマンドラインで期間指定可能（--from/--to）。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など。
    - 合格基準としきい値を定義（例: 稼働率 >= 99.0%）。
    - DB 存在チェック、SQL の OperationalError をハンドルしてフォールトトレラントに動作。
- AI / ニュース NLP:
  - ai.news_nlp:
    - raw_news テーブルからニュースを集約して OpenAI（デフォルト model: gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを追加。
    - 一回の API 呼び出しにつき最大 _BATCH_SIZE=20 銘柄、1 銘柄あたり最大記事数と文字数を制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - レスポンスの JSON バリデーション、スコアの ±1.0 クリッピング、429/ネットワーク断/5xx に対する指数バックオフ（最大リトライ _MAX_RETRIES=3）を実装。
    - 書き込みは対象コードに限定して DELETE → INSERT（部分失敗時に既存データを保護する設計）。
    - ニュース時間ウィンドウ計算ユーティリティ calc_news_window（JST 表現から UTC naive datetime に変換）を用いる。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得。未設定の場合は ValueError を送出。

### Changed
- 監視/実行の DB 接続方針を明確化:
  - 監視 (run_monitoring) は環境にかかわらず monitoring 用の sqlite_path（デフォルト data/monitoring.db）を使用して記録するように設計されている旨を明記。
  - 実行 (run_execution) は paper_trading 環境時に専用 DB を使用して本番 DB と分離する（paper_trading 用 DB が優先）。
- Settings の .env ロード順序:
  - OS 環境 > .env.local（上書き）> .env（未設定のみ）という読み込み優先度を採用。OS 環境変数は保護され、.env.local の override にも保護されたキーは上書きされない。

### Fixed
- 環境変数パースの堅牢化:
  - .env パーサがクォート、エスケープ、コメントの扱いに対応。無効行は無視。
- ポジションサイズ・スケーリング:
  - aggregate cap 適用時に lot_size 単位でスケールダウンし、残余キャッシュを用いて端数を安定的に再配分するロジックを実装（再現性確保のため安定ソートを採用）。

### Security
- 外部 API キー管理:
  - OpenAI API キーは環境変数 OPENAI_API_KEY または明示的引数で渡す必要がある（未設定時はエラー）。
  - 重要な環境変数（例えば OS 側でセットしたもの）は .env による上書きをデフォルトで保護する実装。

### Notes
- 実行方法の概要:
  - 監視: python -m kabusys.run_monitoring（または直接スクリプト実行）でポーリングを開始。
  - 実行エンジン: python -m kabusys.run_execution（または直接スクリプト実行）でセッションを実行。
  - 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数:
  - 必須（起動時に確認される可能性あり）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 推奨/使用: OPENAI_API_KEY, KABUSYS_ENV (development|paper_trading|live), PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- 既知の制約・今後の改善候補（コード内コメントより）:
  - position_sizing: price 欠損時のフォールバック価格（前日終値や取得原価）を将来的に導入する余地がある。
  - lot_size は現在グローバル固定（将来的に銘柄別 lot_map を導入する予定）。
  - ai.news_nlp: DuckDB の executemany 周りの制約に注意（空 params を渡さないなど）。
  - .env 自動ロードはプロジェクトルート検出に依存するため、配布後は挙動が異なる可能性あり（自動ロードを無効化するフラグあり）。

---

（この CHANGELOG はコードの静的解析とコメントから機能を推測して作成しています。実際のリリース履歴を元にする場合はコミットログに基づいて更新してください。）