CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
Semantic Versioning を採用します.

Unreleased
----------

0.1.0 - 2026-04-13
------------------

Added
- 初期リリース: 基本的な自動売買システムのコア機能群を追加。
  - パッケージバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を利用。paper_trading 環境では MockBrokerClient を使用する想定（設定に基づく）。
    - OrderRepository, OrderManager, RiskManager (RiskConfig) , Reconciler を組み立て、ExecutionEngine.run_session() を呼び出してトレードセッションを実行。
    - DuckDB (duckdb.connect) と SQLite を併用してデータ参照・分析を行う。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や整数変換失敗）はデフォルトにフォールバックして警告ログを出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する（監視 DB を常に本番パスで扱う仕様）。
    - プロセス優先度を "high" に設定。SystemMonitor.check_once() を例外ハンドリング付きで定期実行し、KeyboardInterrupt を捕捉してクリーンに終了。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。.env/.env.local を読み、OS 環境変数を保護する仕組みを提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポートする堅牢な実装。
    - Settings クラスで環境変数をラップ（各種パス、API トークン、しきい値、PID/kill flag など）。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装し、不正な値は例外で通知。
    - 主要プロパティ:
      - duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start
      - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
      - env / is_live / is_paper / is_dev
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ有効）

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点は signal_rank 昇順）で候補を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコアが0の場合は等配分へフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限超過時に当該セクターの新規候補を除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 をフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出を実装。
    - risk_based: リスク許容率・損切り率に基づく株数算出。
    - equal/score: ウェイトに基づく割当。lot_size 単位で丸め、max_position_pct や max_utilization などの上限を考慮。
    - aggregate cap 実装: total_cost が available_cash を超える場合はスケールダウンし、端数は lot 単位で remainder 配分を行う。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。
    - 設計上、価格欠損時のログ出力や将来的なフォールバック価格の TODO コメントを含む。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX (Linux/Mac/FreeBSD) を考慮したプロセス優先度設定を実装。psutil を利用し、権限不足や未実装環境では警告ログでフォールバック。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定。入力検証と例外ハンドリングを実装。

- Research（ファクター計算・特徴量探索）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算を実装。200日移動平均やATR、出来高・turnover 指標などを SQL ウィンドウ関数で算出。
    - 計算範囲や不足データ時の None 戻りを明示。

  - research/feature_exploration.py
    - calc_forward_returns: target_date から将来リターン（複数ホライズン）を計算。horizons 引数検証あり。
    - calc_ic / rank / factor_summary: スピアマンのランク相関（IC）計算、値のランク変換（同順位は平均ランク）、基本統計量サマリを実装。外部ライブラリに依存しない純粋実装。

  - research/__init__.py に主要関数をエクスポート（zscore_normalize を含む）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加（CLI）。
    - 指標: 稼働率 (uptime)、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを計算。
    - デフォルトの DB パスは data/paper_trading.db。--db で上書き可能。
    - データ不足時や SQLite の OperationalError を許容するフォールバックを実装し、読みやすいテキストレポートと PASS/FAIL 判定（閾値はソース内定義）を出力。
    - P95 の独自実装、日付フィルタの WHERE 句組立ユーティリティを提供。

- AI ニュース NLP（News Scoring）
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを取得して ai_scores テーブルへ書き込むロジックを実装。
    - バッチサイズ制限、文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 更新戦略（対象コードのみ差し替え）など、堅牢性とフェイルセーフを重視した設計。
    - calc_news_window により JST ベースのニュース収集ウィンドウを UTC naive datetime で計算する実装を追加。
    - 実装は外部の日時関数に依存せずルックアヘッドバイアスを回避する設計。OPENAI_API_KEY 環境変数または引数で API キーを解決。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で提供し、未設定時は明示的に ValueError を送出して不正利用を防止する実装。

Notes / Implementation details
- SQLite と DuckDB の併用:
  - SQLite は主に監視・発注ログ用途、DuckDB は大規模な履歴データ（prices_daily / raw_financials 等）の分析用途として想定。
- .env の自動読み込み:
  - OS 環境変数が優先され、.env.local は .env を上書きする（ただし既に存在する OS 環境変数は保護される）。
- ログと例外ハンドリング:
  - 複数箇所で例外を捕捉してログ出力し、プロセスを停止させずに継続するフェイルセーフ設計（監視ループ、AI スコア取得、DB クエリ等）。
- ドキュメント参照:
  - 各モジュールの docstring に設計方針や参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及あり。

今後の予定（提案）
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価）実装。
- tests（ユニット／統合）の整備。
- ai/news_nlp の DB 書き込み部分や OpenAI エラー細分化の追加ログ強化。
- モニタリング・メトリクスのメトリクス収集バックエンド統合（Prometheus 等）。

---