# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
関連するバージョンはパッケージの __version__（src/kabusys/__init__.py）に従っています。

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・変更点を含みます。

### Added
- 全体
  - プロジェクト初期リリースとして自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定・環境管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードを無効にするための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサー（引用符対応、export プレフィックス対応、インラインコメント処理）を実装。
  - 多数の環境設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル 等）。
  - 環境変数検証を追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェック）。

- 実行用エントリスクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、MockBrokerClient（BrokerClientFactory 経由）で完全に分離して実行。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - 実行に必要なコンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を構築して run_session を実行。
    - duckdb 接続も併用。
    - 監視テーブル存在を保証するため init_monitoring_db を呼び出し（冪等）。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を定期ポーリングして system_status 等を記録。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を設定。

- 監視関連
  - 監視用 DB 初期化ユーティリティ init_monitoring_db を利用して起動時に監視テーブルの存在を保証（冪等）。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows / POSIX の差分を吸収）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
  - 許可エラーや未対応環境でのフォールバック（警告ログ）を備える。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定・重み付け（portfolio_builder）
    - select_candidates（スコア降順、タイブレークに signal_rank）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap（既存保有のセクター露出を計算して上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" をマッピングし、未知の値は警告して 1.0 にフォールバック）。
  - ポジションサイズ計算（position_sizing）
    - calc_position_sizes（risk_based / equal / score の allocation 方法をサポート、単元株丸め、per-stock 上限、aggregate cap のスケーリング、cost_buffer の考慮、lot 単位での端数処理）。

  - これらはすべて純粋関数（DB 参照なし、メモリ内計算）として実装。

- リサーチ（src/kabusys/research/*）
  - ファクター計算モジュール（factor_research）
    - calc_momentum（1m/3m/6m リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）、calc_value（PER/ROE）。
    - DuckDB の prices_daily / raw_financials テーブルを使用する設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）、calc_ic（Spearman ランク相関による IC 計算）、rank、factor_summary（基本統計量）。
    - pandas 等の外部ライブラリに依存せず実装。
  - zscore_normalize を kabusys.data.stats からエクスポートして統合。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、1 銘柄あたり最大記事数／文字数でトリム。
    - 最大 _BATCH_SIZE（20）銘柄ずつ API にバッチ送信、JSON Mode 出力検証、スコアを ±1.0 にクリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - 書き込みは部分失敗を避けるため対象コードを限定して ai_scores テーブルを置換（DELETE → INSERT）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
  - 稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（avg/max/P95）を集計して PASS/FAIL を判定するレポートを標準出力へ出力。
  - デフォルト DB は data/paper_trading.db、--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
  - P95 計算、NULL 安全性、OperationalError のフォールバックを実装。

### Changed
- 実行時のプロセス優先度設定が起動シーケンスの最初で行われるように統一（run_execution.py / run_monitoring.py）。
- 実行エンジン・監視で monitoring DB 初期化（init_monitoring_db）を必ず呼ぶことで監視テーブルの存在を保証（冪等）。
- 設定の読み込み順序を明確化（OS 環境 > .env.local > .env）。OS 環境変数は protected として上書き防止。

### Fixed
- env ファイルパーサの不具合対応:
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理、キーが空の場合のスキップ等の細かいケースに対応。
- position_sizing の aggregate cap スケーリング処理での端数配分ロジックを実装（lot 単位で再配分し、remaining_cash を安全に消費）。
- risk_adjustment.apply_sector_cap で unknown セクターを除外しないことで不意のブロックを回避。
- research / feature_exploration の入力検証（horizons の型・範囲チェック）を強化。
- ai/news_nlp の API キー未設定時に明確なエラーを返すよう改善。

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数でのみ受け取り。ソース内にハードコードはなし。

### Notes / Known limitations
- Monitoring は意図的に本番 sqlite_path を使用する（KABUSYS_ENV に関係なし）。Paper trading 向けに監視を分離したい場合は別途設定を導入する必要あり。
- position_sizing の price 欠損（0.0）時はエクスポージャーが過少に見積もられる可能性がある旨を TODO コメントで記載。将来的にはフォールバック価格を導入予定。
- ai/news_nlp は gpt-4o-mini と JSON Mode を前提とした実装（API レスポンスフォーマットに厳密）。外部 API の仕様変更に依存。

---

（今後のリリースには Unreleased セクションを更新してください。）