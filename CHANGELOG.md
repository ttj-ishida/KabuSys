# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定したリリースごとに履歴を残します。

## [Unreleased]

- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 2026-04-09

初回公開リリース。

### Added
- 全体
  - パッケージ kubusys の初期実装を追加。モジュール群を統合した自動売買／リサーチ基盤の骨格を提供。
  - __version__ を 0.1.0 に設定。

- 環境設定 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（export 形式、クォート/エスケープ、インラインコメントの取り扱いに対応）。
  - 環境変数必須チェック用の _require() を実装。
  - 各種設定プロパティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須値取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション。
    - DBパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視設定（PID_FILE_PATH, KILL_FLAG_PATH 等）、リソース閾値（CPU/MEM/DISK）など。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
  - 環境変数による保護機構（読み込み時に OS 環境変数を protected として上書きを防止）。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（同点時は signal_rank 昇順）による候補選定を追加。
    - calc_equal_weights: 等金額配分の重み計算を追加。
    - calc_score_weights: スコア比率に基づく重み化。全銘柄のスコアが 0 の場合は等金額配分へフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター時価比率が閾値を超える場合に新規候補を除外）。"unknown" セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: 株数計算（allocation_method: "risk_based" / "equal" / "score" をサポート）、単元株（lot_size）で丸め、max_position_pct や max_utilization による上限、cost_buffer を考慮した aggregate キャップとスケーリングの実装。
    - aggregate スケールダウン時に lot_size 単位で残差を再分配するアルゴリズムを実装。

- リサーチ／ファクター計算 (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB を用いて計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を正しく扱う）。
    - calc_value: raw_financials から最新の財務データを参照して PER/ROE を計算（EPS が 0/欠損のときは None）。
    - DuckDB を用いた SQL ベース実装で、prices_daily/raw_financials テーブルのみ参照（外部 API 不使用）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（None/欠損/非有限値を除外、十分なレコード数がなければ None）。
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数点の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ実装。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - news_nlp:
    - score_news: raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込み。バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx）、レスポンス検証、±1.0 でクリップ、部分失敗時に既存スコアを保護する差分 DELETE→INSERT ロジック等を実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（look-ahead バイアス回避のため datetime.today() を参照しない）。
    - テスト用に _call_openai_api を差し替え可能な設計。
  - regime_detector:
    - score_regime: ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で market_regime テーブルへ冪等書き込み。マクロ抽出はキーワードベース、API 失敗時は macro_sentiment=0.0 でフォールバック。
    - 内部実装は news_nlp の補助関数 calc_news_window を利用するが、OpenAI 呼び出しは独立実装としてモジュール結合を最小化。
    - レジーム合成ロジックと閾値に基づくラベル付け（bull/neutral/bear）を実装。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite 用の監視テーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを冪等に作成する初期化関数を追加。

- パッケージエクスポート
  - 各モジュールから主要な関数をパッケージレベルでエクスポート（kabusys.portfolio, kabusys.research, kabusys.ai など）。

### Changed
- 設計上の注意点やフェイルセーフの追加
  - ルックアヘッドバイアス回避: ニュース／レジーム関連処理で datetime.today()/date.today() を参照しない設計を徹底。
  - OpenAI API 呼び出しでのエラー種別に応じたリトライ方針と指数バックオフを実装。
  - DuckDB executemany に関する互換性考慮（空リストの処理を回避）。

### Fixed
- レスポンスパース耐性の強化
  - news_nlp の JSON Mode 応答で前後に余計なテキストが含まれる場合に最外の {} を抽出して復元する処理を追加（実用的エラー回復）。
- データ不足時の安全なフォールバック
  - regime_detector の MA200 計算や各種ファクター計算で過少データ時に中立値を使い WARNING を出すようにし、誤判定や例外発生を防止。

### Security
- 現時点でセキュリティ修正はありません。
  - 注意: OpenAI API キーは環境変数（OPENAI_API_KEY）または明示的引数で与える設計。キー管理はユーザー側で行ってください。

### Notes / Migration
- 環境変数:
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
  - 必須の機密情報（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は _require() により未設定時に ValueError を投げます。
- DuckDB / SQLite:
  - research/ai モジュールは DuckDB 接続、monitoring は sqlite3.Connection を直接受け取る API です。呼び出し側で接続を用意してください。
- テストフック:
  - OpenAI 呼び出しの関数（ニュースとレジーム検出共に _call_openai_api）を unittest.mock.patch で差し替えてテスト可能。

---

今後の予定（例）
- 銘柄ごとの単元株サイズをマスタから取得して個別 lot_size をサポートする拡張。
- PBR や 配当利回りなどバリューファクターの追加。
- ai モジュールのレスポンス検証・フォールバックロジックのさらなる堅牢化。

（以上）