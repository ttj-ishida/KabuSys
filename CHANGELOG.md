CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。日付はリリース日です。

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- プロジェクト初期リリース。以下の主要コンポーネントを追加しました。
  - 実行/監視ランチャー
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine.run_session() 呼び出しを実装。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority）。
      - duckdb 結合 (duckdb.connect) を使用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
      - 起動時にプロセス優先度を "high" に設定。
      - SQLite / DuckDB の接続初期化とクリーンなクローズ処理を実装。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
      - 読み込み優先度: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - export に対応した .env パーサ実装（クォート処理、エスケープ、インラインコメント処理を考慮）。
      - Settings クラスを導入し、環境変数をプロパティとして扱う（各種デフォルト値とバリデーションを含む）。
      - 重要設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 必須、PAPER_FILL_MODE の有効値検証、KABUSYS_ENV/LOG_LEVEL の検証、データベースパス・監視用パス等のデフォルト値を提供。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順で候補選別（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計 0 の場合はフォールバックで等配分）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限を考慮して候補を除外するロジック。既存保有のエクスポージャー算出や売却予定銘柄の除外を考慮。
      - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供。未知のレジームは警告とともに 1.0 でフォールバック。
    - portfolio.position_sizing
      - calc_position_sizes: weight／candidates を元に発注株数を算出。risk_based / equal / score の各モードをサポート。lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap スケーリング、残差処理による追加配分ロジックを含む。
  - 研究・ファクター計算
    - research.factor_research
      - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算関数を実装。欠損データに対する安全な扱い（必要行数未満は None）を行う。
    - research.feature_exploration
      - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズンを一括取得）。
      - calc_ic / rank / factor_summary: ランク相関（Spearman）計算、ランク付け、基本統計量集計を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research.__init__ により主要関数をエクスポート。
  - AI ニュース NLP
    - ai.news_nlp
      - raw_news と news_symbols を参照して銘柄ごとのニュースを集約、OpenAI (gpt-4o-mini) でセンチメントスコアを算出して ai_scores に保存する機能を実装。
      - 処理: タイムウィンドウ計算（JST ベースのウィンドウ → UTC に変換）、記事トリム（最大記事数・最大文字数制限）、バッチ（最大 20 銘柄）での API 呼び出し、JSON Mode 出力のバリデーション、スコアの ±1.0 クリップ、部分失敗を防ぐための部分的な置換（DELETE→INSERT）戦略を採用。
      - API の 429/ネットワーク/5xx に対する指数バックオフでのリトライ実装。OpenAI API キー未設定時は ValueError を送出。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収しプロセス優先度を設定。未対応 OS や権限不足時は警告を出してスキップ。
      - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティ。引数検証と権限例外処理を実装。
  - ツール
    - tools.paper_verification_report
      - Paper Trading 用検証レポート生成 CLI を実装。デフォルト DB は data/paper_trading.db。期間フィルタ（--from / --to）をサポート。
      - 指標: 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）など。閾値による PASS/FAIL 判定を出力。
      - レポート内で SQL の実行失敗（テーブル無し等）を安全に扱うフォールバックを実装。

Changed
- 初回リリースのため「Changed」は特になし。

Fixed
- 初回リリースのため「Fixed」は特になし。

Security
- OpenAI API キーの取り扱いについて、明示的に引数経由または環境変数 OPENAI_API_KEY を要求する実装とし、未設定時に早期エラー（ValueError）を発生させることで誤使用を抑制。

Notes / 重要な挙動
- .env の自動ロードはプロジェクトルートが検出できない場合にスキップされます（パッケージ配布後も安全に動作するよう配慮）。
- run_monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使うため、監視データは paper_trading DB と分離されません。paper_trading 用操作は run_execution 側で paper_sqlite_path を使用して分離しています。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかでなければならず、不正な値は起動時に例外を送出します。
- position_sizing の aggregate cap 処理は lot_size 単位での丸めと残差配分ロジックを含み、available_cash を超えないよう安全にスケーリングします。
- ai.news_nlp は大量テキスト送信によるトークン肥大化を防ぐため、1 銘柄あたりの記事数・文字数に上限を設けています。

開発者向けメモ
- 各モジュールは可能な限り外部副作用を抑え、DuckDB/SQLite 接続や外部 API 呼び出しを呼び出し元に委ねる設計になっています。ユニットテストを容易にするため、純粋関数（portfolio, research の多く）は DB を参照せず入力データに対して deterministic な計算を行います。
- DuckDB を利用したファクター計算は SQL ウィンドウ関数を多用しており、大規模データでも効率的に処理できる設計です。

今後の予定（例）
- stocks マスタに単元株情報を持たせ、銘柄別 lot_size を取り扱う拡張（position_sizing の TODO）。
- ai.news_nlp のレスポンス検証強化・部分コミット失敗時のロールバック戦略改善。
- 実行中のプロセス管理（pid ファイル/kill flag）の運用ドキュメント整備。

---

フィードバックや不具合報告は issue を作成してください。