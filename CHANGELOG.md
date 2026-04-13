CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠します。  
日付はリポジトリコードの内容から推定したリリース日（現在日: 2026-04-13）を用いています。

Unreleased
----------
（現在のコードベースはバージョン 0.1.0 として初期リリースが行われています。将来の変更をここに記載してください。）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行 / 監視用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV が "paper_trading" の場合、paper_trading 用の専用 SQLite DB を使用し MockBrokerClient を用いる挙動をサポート（本番 DB とは分離）。
    - プロセス優先度を起動直後に "high" に設定するユーティリティ呼び出しを導入。
    - ExecutionEngine 起動前に OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
    - 実行後に SQLite / DuckDB 接続を確実にクローズする finally ブロックを実装。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する点を明記。
    - プロセス優先度を "high" に設定してから監視ループを開始。KeyboardInterrupt により安全に終了し DB をクローズする。

- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を追加。
    - プロジェクトルートは .git または pyproject.toml を探索して特定。
    - .env, .env.local の読み込み順序と上書きルール（OS 環境変数保護）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーはクォート／エスケープ／インラインコメント等を考慮した堅牢な実装。
  - Settings クラスを導入し、環境設定のプロパティ化（duckdb/sqlite/paper_trading path、pid/kill flag、しきい値、PAPER_FILL_MODE 等）。
    - env / log_level / PAPER_FILL_MODE 等の検証を行い不正値で ValueError を送出する。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しを run_execution / run_monitoring で利用し監視テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - SQLite の paper_trading DB からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を集計して標準出力レポートを生成する CLI。
    - CLI オプション --from / --to / --db をサポート。期間フィルタは ISO8601 UTC 文字列に変換してクエリに渡す。
    - 判定基準（稼働率・成功率・P95 レイテンシ等）の閾値が定義され、PASS/FAIL を出力。
    - DB が存在しない場合やテーブルが無い場合に安全に扱うための例外捕捉（sqlite3.OperationalError をハンドリング）。

- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0.0 の場合は等金額配分にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）: 既存保有のセクター別時価から上限超過セクターを除外するロジック（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対する乗数を定義し、未知レジームは 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。
      - allocation_method: "risk_based"（リスクベース）および "equal"/"score" をサポート。
      - lot_size による丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を加味した保守的見積り、残差配分ロジックなどを実装。
      - 価格欠損時はスキップする挙動を明記。

  - portfolio/__init__.py で主要関数をエクスポート。

- 研究・ファクター計算モジュール
  - research/factor_research.py
    - DuckDB を用いたモメンタム・ボラティリティ・バリューファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、結果は (date, code) をキーとする辞書リストで返す。
    - 実装はデータ不足時に None を返す等の堅牢性を持つ。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman 相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - research/__init__.py で zscore_normalize（data.stats）と上記関数をエクスポート。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py を追加。
    - raw_news / news_symbols を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄別のセンチメントスコアを計算し ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - 1銘柄あたりの記事数・文字数上限、バッチサイズ（最大 20 銘柄/コール）、スコアの ±1.0 クリップ、最大リトライ回数、指数バックオフなどを実装。
    - OpenAI クライアント生成は OpenAI(api_key=...) を使用。API キー未設定時は明確なエラーを返す。
    - レスポンスのバリデーションと部分更新（対象コードのみ DELETE→INSERT）により部分失敗時でも既存スコアを過度に上書きしない設計。
    - 実装上の注意点（execuemany の DuckDB の制約、datetime.today() を参照しない設計でルックアヘッドバイアスを回避）を含む。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）をプラットフォーム差分（Windows / POSIX）を吸収して提供。
    - アクセス拒否や未対応機能時は警告を出して処理をスキップする安全な実装。
  - utils/__init__.py を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させることで安全に失敗する設計。

Notes / Known limitations (ドキュメントに明記)
- portfolio/risk_adjustment.apply_sector_cap は price が欠損（0.0）の場合、エクスポージャーを過少見積もる可能性があり将来的にフォールバック価格を導入することを示唆している（TODO コメントあり）。
- DuckDB に対する executemany の制約が存在するため、ai/news_nlp の書き込みは部分的に保護する手法を採用している。
- MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバックする（time.sleep に渡す負の値回避）。
- .env 自動ロードは既定で有効（プロジェクトルートが見つからない場合はスキップ）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

Contributing
- 初期リリース。今後の機能追加・バグ修正は Unreleased セクションに記載してください。