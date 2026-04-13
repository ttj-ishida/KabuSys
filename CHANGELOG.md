# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 初回リリースとして以下の主要機能を実装。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を行う。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 環境・設定管理
  - config.py: 環境変数・.env ファイル自動ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml）。.env/.env.local の読み込み順序と上書きロジック（protected set による OS 環境変数保護）を実装。export 形式、クォート、インラインコメント処理など堅牢な .env パーサを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止に対応。
  - Settings クラスで主要設定をプロパティ化（DB パス、PID ファイル、監視しきい値、PAPER_FILL_MODE 検証、環境種別判定等）。
- 監視関連
  - monitoring_db 初期化呼び出しを run_* スクリプトへ組み込み（冪等に監視テーブルを保証）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（score 降順、signal_rank タイブレーク）、等金額・スコア加重の重み計算を実装。スコア全てが 0 の場合のフォールバック警告を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用ロジック（既存保有のセクターエクスポージャ計算、上限超過セクターの候補除外）。市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear + フォールバック）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、per-position / aggregate cap、コストバッファを考慮したスケーリングロジックを実装。available_cash に対するスケールダウン処理で残差の扱い（lot 単位で追加配分）も実装。
- リサーチ機能（DuckDB を用いる）
  - research/factor_research.py: momentum / volatility / value ファクター計算を実装（prices_daily, raw_financials テーブル参照）。200 日移動平均、ATR、出来高平均などを SQL ウィンドウ関数で算出。データ不足時の None フォールバックを考慮。
  - research/feature_exploration.py: 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ランク化ユーティリティ rank、ファクターサマリーを実装。外部ライブラリに依存せず純粋 Python 実装。
  - research/__init__.py: zscore_normalize のエクスポートを含めた公開 API を整備。
- ニュース NLP（AI スコアリング）
  - ai/news_nlp.py: raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。タイムウィンドウ計算、チャンク処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコア保護のための限定的な DELETE/INSERT ロジックなどを実装。
- ユーティリティ
  - utils/process_priority.py: Windows と POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。権限不足や未対応 OS の場合は警告ログでスキップする安全処理を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定するしきい値（デフォルト）を設定。P95 の計算、日付フィルタ、DB 存在チェック、出力フォーマットを実装。コマンドライン引数(--from/--to/--db)に対応。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Notes / Configuration defaults & behaviour
- 環境変数とデフォルト:
  - KABUSYS_ENV: development / paper_trading / live（無効値は例外）
  - SQLITE_PATH: data/monitoring.db（監視用、本番パス）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 実行時は専用 DB を使用）
  - DUCKDB_PATH: data/kabusys.duckdb
  - PID_FILE_PATH / KILL_FLAG_PATH 等のデフォルトを設定
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL: ポーリング秒数（1 以上の整数のみ許容、無効値時は 60 秒にフォールバック）
- セキュリティ / 安全策:
  - .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - process_priority や CPU affinity の設定は失敗しても例外を投げずログでスキップする（運用環境での安全性確保）。
  - ai/news_nlp の OpenAI API キーは明示的に渡すか OPENAI_API_KEY 環境変数を設定する必要がある。未設定時は ValueError を送出。

---

これらはコードベースから推測される初期機能群の要約です。使用法や環境変数の詳細は各モジュール内の docstring / コメントを参照してください。