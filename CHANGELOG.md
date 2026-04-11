CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、意味的バージョニングを想定しています。

Unreleased
----------

（現時点で未リリースの作業はありません）

0.1.0 - 2026-04-11
-----------------

初回リリース。コードベースから推測される主要機能・挙動・注意点をまとめます。

Added
- 基本情報
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を定義。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートの .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - 高度な .env パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを提供し、以下をプロパティ経由で取得:
    - J-Quants / kabu API / LINE API 関連（必須・任意の env 取り扱い）
    - DB パス: DUCKDB_PATH（duckdb）、SQLITE_PATH（monitoring 用）
    - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（KABUSYS_ENV=paper_trading 時に使用）
    - PAPER_FILL_MODE の検証（instant|partial|never|reject のみ有効）
    - 監視関連ファイルパス・閾値（PID/killflag、CPU/MEM/DISK の閾値）
    - KABUSYS_ENV 検証: 有効値は development / paper_trading / live
    - LOG_LEVEL 検証

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
    - process priority を最初に "high" に設定
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory を用いたブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine.run_session 呼び出し
    - デフォルトの RiskConfig 値（max_position_pct 等）を設定し、initial_portfolio_value は broker.get_available_cash() を使用
    - 起動時に監視テーブル（init_monitoring_db）を冪等に作成
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用
    - プロセス優先度設定、SQLite/DuckDB 接続初期化、例外ハンドリング、KeyboardInterrupt 対応

- ユーティリティ（kabusys.utils）
  - process_priority.py:
    - set_process_priority(level) — Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定
    - set_cpu_affinity(cpu_count) — 指定数コアへのピニング（None で何もしない）
    - 権限不足や未対応 OS に対する安全なフォールバック（警告ログ）
  - cross-platform の取り扱い（psutil に依存）

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py:
    - select_candidates — スコア降順かつ signal_rank によるタイブレークで候補選定
    - calc_equal_weights / calc_score_weights — 等ウェイト・スコア加重（スコア合計が 0 の場合は等金額にフォールバック）
  - position_sizing.py:
    - calc_position_sizes — allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ）考慮、余剰キャッシュによる端数配分ロジック
  - risk_adjustment.py:
    - apply_sector_cap — セクター上限（max_sector_pct）を超える場合に当該セクターの新規候補を除外（"unknown" セクターは上限適用除外）
    - calc_regime_multiplier — レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）

- リサーチ機能（kabusys.research）
  - factor_research.py:
    - calc_momentum — 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）
    - calc_volatility — 20 日 ATR / ATR 比率、平均売買代金、出来高比
    - calc_value — PER/ROE（raw_financials と prices_daily を組合せ）
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算
  - feature_exploration.py:
    - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括計算
    - calc_ic / rank / factor_summary — スピアマンランク相関（IC）、ランク計算、基本統計量（count/mean/std/min/max/median）
  - 設計方針: DuckDB 接続のみ参照し、外部ライブラリ（pandas 等）に依存しない純 Python 実装

- AI / NLP 機能（kabusys.ai）
  - news_nlp.py:
    - calc_news_window — target_date に対応するニュース収集ウィンドウ（JST→UTC 変換）
    - score_news — raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_scores）を書き込む
      - バッチ処理（最大 20 銘柄/チャンク）、1銘柄当たり記事数と文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - API の 429/タイムアウト/ネットワーク/5xx に対する指数バックオフのリトライ
      - レスポンスの厳格なバリデーション（JSON 抽出・results 構造・コード整合性・数値チェック）
      - スコアを ±1.0 にクリップし、ai_scores テーブルへ部分的（取得成功コードのみ）に置換（DELETE して INSERT）することで部分失敗に強い
      - OpenAI API キー未設定時は ValueError を送出
      - DuckDB の executemany に空リストが渡せない問題へのワークアラウンド（空チェック）
  - regime_detector.py:
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを重み付け（MA 70% / Macro 30%）して日次の market_regime ('bull'/'neutral'/'bear') を判定し、冪等的に market_regime テーブルへ書き込み
    - LLM コール失敗時には macro_sentiment を 0.0（中立）として継続
    - prices_daily クエリは target_date 未満のデータのみを使用してルックアヘッドバイアスを防止

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）  
  - ただし実装上、.env 読み込み失敗時の警告や process priority / cpu affinity の権限エラーに対して安全にスキップする動作が明示されている。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや機密環境向け）。

Compatibility / Requirements
- 外部依存:
  - duckdb
  - psutil
  - openai（OpenAI Python クライアント）
  - 標準ライブラリ: sqlite3, logging, os, time など
- DuckDB のバージョン差分（executemany の挙動）へ配慮した実装あり。
- POSIX/Windows 両対応だが、一部機能（プロセス優先度・CPU affinity）は OS 権限や実行環境に依存し、失敗した場合はログを出してスキップされる。

Migration / Notes for users
- 環境変数の名称・既定値:
  - KABUSYS_ENV: development / paper_trading / live（無効値は例外）
  - PAPER_FILL_MODE: instant / partial / never / reject（無効値は例外）
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH のデフォルトは data/ 以下
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）、正の整数のみ有効。デフォルト 60 秒。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使えば .env 自動ロードを抑制可能
- Paper trading:
  - KABUSYS_ENV=paper_trading のとき、run_execution は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離
- モデル・API:
  - news_nlp / regime_detector は gpt-4o-mini を想定。API 呼び出し時のリトライやフォールバック動作を持つが、API 利用にはキーとネットワークが必要。
- DuckDB に書き込む際、部分的にコードのみを更新することで部分失敗時のデータ保全を図る設計になっている（ai_scores の置換ロジック等）。

今後の改善候補（コードから推測）
- 銘柄別 lot_size を stocks マスタで持たせる拡張（position_sizing の TODO）
- price 欠損時のフォールバック（前日終値や取得原価）を導入してエクスポージャー過小見積りを防止（risk_adjustment の TODO）
- AI モジュールの OpenAI クライアント抽象化（テスト容易化・差し替え性向上）
- DuckDB クエリのパフォーマンスチューニング（インデックス・並列処理検討）

---

注: 本 CHANGELOG は提示されたソースコードから実装を推測して作成したもので、実際のリリースノートとは異なる場合があります。必要であれば日付やリリース番号、より詳細な変更点（コミット単位）に合わせて修正します。