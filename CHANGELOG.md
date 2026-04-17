# Changelog

すべての注目すべき変更履歴をここに列挙します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回公開リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ全体
  - 初期バージョンとして kabusys v0.1.0 を追加（src/kabusys/__init__.py の __version__）。
  - パッケージの公開用エクスポートを定義（portfolio、execution、monitoring 等）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。Engine をスレッドで起動し、data/stop_requested.flag による停止制御、execution.pid の管理を行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する挙動を実装。
    - BrokerClientFactory を利用してブローカークライアントを作成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を定義し、初期 portfolio value を broker.get_available_cash() で取得する設計。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。例外はログに残して次回ポーリングに継続。

- 設定管理
  - config.py
    - .env / .env.local 自動ロード機構を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。OS 環境変数は保護され、.env.local は上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 複雑な .env パースを実装（export KEY=、引用符で囲まれた値のエスケープ、インラインコメントの扱い等）。
    - Settings クラスを追加し、アプリケーション設定（API トークン、DB パス、paper trading 設定、監視閾値、環境チェック、LOG_LEVEL 検証など）をプロパティとして提供。settings インスタンスをエクスポート。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。Windows / POSIX（Linux/Mac/FreeBSD）対応。失敗時は警告ログでフォールバック。
    - set_cpu_affinity: 指定コア数へ CPU affinity を設定する補助関数を追加。権限不足や未対応プラットフォームでは警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 銘柄選定と重み計算の純粋関数を追加: select_candidates（スコア降順、タイブレークルール）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合のフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター集中が上限を超える場合に該当セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すロジックを実装（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - lot_size 単位での丸め、per-position と aggregate の上限、cost_buffer を用いた保守的コスト見積り、available_cash を超える場合のスケーリングと端数処理（残余キャッシュで lot_size 単位を追加配分）をサポート。
    - risk_based 方式では損切り率 stop_loss_pct と risk_pct を用いた株数計算を実装。

- 研究（Research）
  - research/factor_research.py
    - DuckDB を用いたファクター計算を実装。calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、流動性指標）、calc_value（PER/ROE）を追加。
    - 大量データ処理を考慮したスキャン範囲・ウィンドウ設計を採用。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、IC 検定 calc_ic（Spearman の ρ）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py で主要 API をエクスポート（zscore_normalize を data.stats から再エクスポート含む）。

- AI ニュース NLP
  - ai/news_nlp.py（ニュースセンチメントスコアリング）
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのスコアを ai_scores に書き込む処理を実装。
    - スコアのクリッピング（±1.0）、バッチサイズ、1 銘柄あたりの文字数・記事数上限、429/ネットワーク断/5xx への指数バックオフリトライ、レスポンス検証などの設計を含む。
    - calc_news_window によるニュース収集ウィンドウ（JST → UTC 変換）を実装。
    - （ファイル末尾が断ち切られているため実装途中の箇所がある可能性あり。詳細は実装ファイル参照。）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99%、成功率 90% など）に基づき PASS/FAIL を判定して出力。
    - --from / --to / --db オプションをサポート。DB が存在しない/テーブルが欠如している場合は適切に N/A を表示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 設定ロードとパースの堅牢化（quoted 値のエスケープや export プレフィックス、インラインコメントの扱いなど）により .env による設定ミスの緩和を図った。

### Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map が欠損（価格 0.0）の場合にエクスポージャーが過少見積りされ、ブロックが外れる可能性がある旨をコメントで指摘。将来的には前日終値や取得原価でのフォールバックを検討。
- ai/news_nlp.py:
  - 大枠は設計済みだが、ソース末尾が断ち切られているため（コードが途中で終わっている）、いくつかの実装・エラーハンドリング処理は未完の可能性あり。実行前にファイル末尾の実装状況を確認してください。
- DuckDB / SQLite のスキーマ依存:
  - research・AI・ツール系は prices_daily / raw_financials / raw_news / trade_logs / system_status 等のテーブルを前提としているため、本番運用前にスキーマ整備を行ってください。
- クロスプラットフォーム挙動:
  - process_priority や cpu_affinity は権限やプラットフォームに依存。権限不足時は警告を出して処理をスキップする設計。

### Migration / Environment
- 新たに使用する主な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper trading デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL（run_monitoring ポーリング間隔、秒。デフォルト 60）
  - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
  - OPENAI_API_KEY（ai/news_nlp の API キー）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると .env 自動読み込みを無効化）
- デフォルト挙動:
  - run_monitoring は KABUSYS_ENV に関わらず sqlite_path（本番）を使用する設計である点に注意してください。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して DB を分離。

---

以上。必要なら各項目をさらに細かく分けてファイル単位の変更点や関数シグネチャの差分一覧を作成できます。どの形式（より簡潔/詳細）で出力するか指定してください。