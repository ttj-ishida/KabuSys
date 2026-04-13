Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。  

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で整理しています。
- 日付はリリース日時（yyyy-mm-dd）を使用しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本モジュールの初期実装（初回公開）。
  - パッケージ版情報: kabusys.__version__ = "0.1.0"。
- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。プロセス優先度を起動直後に "high" に設定し、SQLite / DuckDB に接続して実行セッションを開始するワークフローを実装。
    - Paper Trading 環境 (KABUSYS_ENV=paper_trading) は本番 DB と分離し、デフォルトで data/paper_trading.db を使用（MockBrokerClient を使用する想定）。
    - 注文関連の主要コンポーネントを組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
    - RiskManager のデフォルト設定を含む（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や非数はデフォルトにフォールバック）。
    - 監視用 DB は環境にかかわらず設定されている sqlite_path（本番パス）を使用する仕様。
    - プロセス優先度を起動時に "high" に設定。
- 設定 / 環境
  - config.Settings: 環境変数読み込みとラッパーを提供。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env / .env.local を読み込む（OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサの強化: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
    - 多数の設定プロパティを公開（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEMORY/DISK 閾値 / LOG_LEVEL / KABUSYS_ENV 等）。各プロパティでバリデーションを実施（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋signal_rank タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア全てが 0 の場合は等配分にフォールバックし警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を抑えるフィルタ（既存ポジションのセクター露出を計算し、上限を超えるセクターの新規候補を除外）。unknown セクターは制限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した保守的見積り、残差処理による追加配分などを実装。
- 研究（Research）モジュール
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを利用した各種ファクター計算（1M/3M/6M リターン、MA200 乖離、ATR20、平均売買代金、PER/ROE 等）。
    - データ不足時の None 扱い、ウィンドウ幅やスキャン範囲の工夫（カレンダーバッファ）を実装。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算（horizons 検査あり）。
    - calc_ic: Spearman ランク相関（IC）計算（有効レコード数 3 未満で None）。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- AI / ニューススコアリング
  - ai.news_nlp:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを取得し ai_scores に書き込む処理を実装。
    - バッチサイズ 20、記事・文字数の制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、スコアクリップ（±1.0）。
    - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンス検証、部分的書き換え（対象コードだけ DELETE → INSERT）で失敗時の影響を限定。
    - ニュース収集ウィンドウを JST ベースで計算（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定を提供。未対応 OS や権限不足時には警告を出してスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定機能（安全チェックと例外ハンドリング）。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI。期間指定（--from/--to）や --db オプションで DB パスを指定可能。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等を集計し、閾値に基づいた PASS/FAIL 判定を出力。デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）。

Changed
- 初期リリースにつき、既存プロジェクトへの互換性に関する特記事項:
  - 監視用スクリプトは環境にかかわらず Settings.sqlite_path（本番パス）を使用する挙動であることを明示。

Fixed
- 初期リリースにつき、既知の不具合修正履歴はなし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で提供することを要求。キー未設定時はエラーとなる実装（安全側の設計）。

Notes / 備考
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴に基づくものではありません。細かな実装意図や追加の変更点は git 履歴やレビューコメントを参照してください。