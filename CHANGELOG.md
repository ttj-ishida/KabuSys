# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
リリースは semver に従います。

## [Unreleased]

## [0.1.0] - 2026-04-11
初回リリース

### Added
- 全体
  - パッケージバージョンを 0.1.0 に設定（kabusys.__version__）。
  - DuckDB / SQLite を利用した研究・監視・実行ワークフローの基盤を実装。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する。
    - 起動時にプロセス優先度を設定（高優先度）。
    - SQLite / DuckDB 接続の初期化とクリーンなクローズ処理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用の SQLite DB を使用し、MockBrokerClient（ブローカー分離）を利用する運用をサポート。
    - 起動時にプロセス優先度を設定（高優先度）。
    - ExecutionEngine 起動のためのコンポーネント組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を実装。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義し、初期ポートフォリオ値をブローカー残高から取得。

- 設定管理
  - kabusys.config.Settings
    - OS 環境変数とプロジェクトルートの .env / .env.local を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env パーサーはコメント・クォート・export 形式に対応し、安全に環境変数をロード。
    - 必須環境変数取得用の helper（_require）を提供（未設定時は ValueError）。
    - 各種設定プロパティを実装:
      - API トークン / パスワード（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - Paper Trading の挙動（PAPER_FILL_MODE の検証: instant, partial, never, reject）
      - 監視関連ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH 等）と閾値（CPU/MEMORY/DISK）
      - 環境（KABUSYS_ENV）の検証（development, paper_trading, live）
      - ログレベル（LOG_LEVEL）の検証
    - settings = Settings() をモジュールレベルでエクスポート。

- プロセス制御ユーティリティ
  - kabusys.utils.process_priority
    - cross-platform（Windows / POSIX）でプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder
    - 銘柄選定関数 select_candidates（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING 表示）。
  - kabusys.portfolio.position_sizing
    - 各銘柄の発注株数算出 calc_position_sizes を実装。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - cost_buffer を考慮した保守的見積もりと aggregate cap 超過時のスケールダウン（残余キャッシュを用いた再配分のロジック含む）。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（売却予定銘柄をエクスポージャー計算から除外可能）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知は 1.0 でフォールバック）。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - DuckDB 接続を受け取り価格・財務データからファクターを計算する関数群を追加:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（ウィンドウ不足時は None）。
      - calc_value: PER / ROE（raw_financials から最新レコードを結合）。
    - 各関数は (date, code) を持つ dict リストを返す。
  - kabusys.research.feature_exploration
    - 将来リターン calc_forward_returns（任意 horizon の一括取得、入力検証あり）。
    - スピアマンランク相関による IC 計算 calc_ic（有効レコード < 3 の場合は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median の統計要約。
  - research パッケージの __all__ に必要なエクスポートを追加。

- AI 関連
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む score_news を実装。
    - 動作特徴:
      - 対象ウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」を UTC に変換して使用（calc_news_window）。
      - 1銘柄あたり記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 1 API 呼び出しで最大 20 銘柄をバッチ処理。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）。
      - レスポンスの JSON バリデーションとスコアクリッピング（±1.0）。
      - 書き込みは冪等かつ部分失敗で既存データを破壊しないよう、対象コードを限定した DELETE → INSERT のトランザクションで実行。
      - OpenAI API キーが未設定の場合は ValueError を送出。
      - API 呼び出し部分はテスト容易性を考慮して _call_openai_api を分離。
  - kabusys.ai.regime_detector
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定して market_regime テーブルへ書き込む機能を追加。
    - マクロニュース抽出のためのキーワードセットと OpenAI 呼び出し（gpt-4o-mini）、合成スコアのクリッピング、閾値判定ロジックを実装。
    - API 失敗時は macro_sentiment=0.0 として継続（フォールトトレラント）。

### Changed
- データベース初期化
  - monitoring 用テーブルは起動スクリプト実行時に init_monitoring_db を呼んで存在を保証する（冪等な初期化）。

### Fixed
- 入力検証・堅牢化
  - 環境変数パーサーでのクォート/エスケープ/コメント処理を改善し、.env 読み込み失敗時に警告で安全に処理を継続。
  - OpenAI API レスポンスパース時に前後余分テキストが混入するケースを部分的に復元する処理を追加（最外の {} を抽出して再パース）。
  - DuckDB executemany での空パラメータ禁制を回避するガードを追加（空リストを渡さない）。

### Security
- OpenAI API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を使用する設計。未設定時はエラーとなるため、キー管理に注意すること。

---

注記:
- ドキュメント内やコードに TODO / 将来拡張のコメントが含まれます（例: 銘柄別 lot_size のサポート、価格欠損時のフォールバック等）。将来のリリースで改善予定です。
- 実行環境依存（OS 権限等）で一部機能（プロセス優先度、CPU affinity）が制限される場合があります。権限不足時は警告を出して安全にスキップします。