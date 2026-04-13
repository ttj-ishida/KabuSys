# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog の形式に従います。  

※ バージョン番号は src/kabusys/__init__.py 内の __version__ に合わせています。

## [0.1.0] - 2026-04-13

### 追加
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db をデフォルトで分離）。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動する。

- 設定・環境変数管理モジュール
  - config.py を追加。
    - .env/.env.local の自動ロード機構（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env パーサは export 構文、クォート文字列、インラインコメント等に対応。
    - OS 環境変数を保護するための上書き制御を実装。
    - Settings クラスを提供。多くの環境変数の取得ロジックとバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
    - DB パス、PID/KILL フラグ、リソース閾値（CPU/MEM/DISK）などをプロパティで提供。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights を実装（スコア全体が 0 の場合のフォールバックあり）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用するフィルタ。
    - calc_regime_multiplier: market レジームに応じた資金乗数を計算（bull/neutral/bear、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数計算を実装（risk_based / equal / score）。
    - lot_size（単元）で丸め、per-position 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 残差配分を安定的に行うアルゴリズムを導入。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) 実装（Windows / POSIX を吸収）。
    - set_cpu_affinity(cpu_count) 実装（最初の N コアに固定、権限不足等は警告してスキップ）。

- リサーチ・ファクター計算
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、volume 等）、バリュー（PER/ROE）計算関数を DuckDB を使って実装。
    - データ不足時の None ハンドリング・ウィンドウ制限を実装。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman）計算 calc_ic、ランク付け rank、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news テーブルを元に OpenAI (gpt-4o-mini) を用いたセンチメントスコアリング機能を実装。
    - 銘柄ごとの記事集約、バッチ処理（最大 20 銘柄/コール）、最大トークン対策（記事数・文字数トリム）、リトライ戦略（429/ネットワーク/5xx）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 書換保護（対象コードのみ置換）などフェイルセーフ設計。
    - target_date ベースのニュースウィンドウ計算関数 calc_news_window を提供。
    - APIキーは引数または環境変数 OPENAI_API_KEY で指定。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、リスク却下件数、P95 レイテンシ等を集計・判定（閾値による PASS/FAIL を出力）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。

### 変更
- 起動時のデフォルト動作
  - 監視 (run_monitoring) は意図的に本番 sqlite_path を使用する設計に明示（環境に依存せず監視を本番 DB で行う）。
  - run_execution は paper_trading 環境で DB を明確に分離（paper_sqlite_path を使用）。これにより paper_trading が本番 DB に影響しないことを保証。

### 修正
- 環境変数 / 設定の堅牢性を強化
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）に対して警告を出しデフォルトにフォールバックするように変更。
  - PAPER_FILL_MODE の無効値に対して ValueError を発生させるバリデーションを追加。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックを実装。
  - .env 読み込みでファイルが読めない場合に警告を出すように変更。

- DB 初期化の冪等性
  - run_execution / run_monitoring 起動時に init_monitoring_db を呼び出し、監視テーブルが存在することを保証（冪等）。

- ロギングとエラーハンドリング
  - monitor.check_once() の予期しない例外はログ出力して次のポーリングを継続するように保護。
  - process_priority / cpu_affinity の設定で権限不足や未対応 OS の場合に警告してスキップするように変更。

### 既知の注意点 / 制限
- ai/news_nlp.py は OpenAI API を使用する実装であり、API キー未設定時は例外が発生する（ユーザに明示）。
- position_sizing の一部（price が欠損の場合のフォールバック）は TODO コメントとして残してあり、将来的に前日終値や取得原価などのフォールバック実装が検討される。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（テスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能）。

---

今後のリリースでは、テストケースの追加、パフォーマンス最適化、銘柄別 lot_size の導入、AI スコア生成の部分リトライの改善などを予定しています。