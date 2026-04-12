CHANGELOG
=========

すべての重要な変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
  - 実行系
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を利用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離する。
      - 実行開始時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
      - ExecutionEngine の組み立て: BrokerClientFactory, OrderRepository, OrderManager, RiskManager（RiskConfig のデフォルト値を含む）, Reconciler を統合してセッションを実行。
      - duckdb と sqlite3 の両方の接続を利用。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値（0以下や非整数）はデフォルトにフォールバックし警告を出力。
      - 監視処理は実行環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する。
      - 起動時にプロセス優先度を High に設定。
  - 設定管理
    - config.Settings: 環境変数／.env の読み込み・ラップを実装。
      - プロジェクトルートを .git または pyproject.toml から自動判定し、自動で .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env パーサは export 形式、クォート文字列、インラインコメントを扱える堅牢な実装。
      - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV 等）および基本的なバリデーション。
  - ポートフォリオ構築
    - portfolio モジュール（純関数群）を追加:
      - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
      - position_sizing: calc_position_sizes
        - risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積りなどを実装。
      - risk_adjustment: apply_sector_cap, calc_regime_multiplier
        - セクター集中制限の適用（当日売却予定銘柄の除外や "unknown" セクターの扱い）、市場レジームに基づく投下資金乗数（bull/neutral/bear のマップ）を実装。
  - 研究（Research）モジュール
    - research.factor_research:
      - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを用いて各種ファクター（モメンタム、ATR、出来高、PER/ROE 等）を計算。
    - research.feature_exploration:
      - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（ランク付け：同順位は平均ランク）を実装。
      - pandas 等の外部依存を持たず標準ライブラリ＋DuckDB で完結する実装方針。
    - research.__init__ で主要 API をエクスポート（zscore_normalize を含む）。
  - AI ニュース NLP
    - ai.news_nlp:
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
      - バッチサイズ、記事数/文字数上限、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンスの厳密な JSON バリデーションなどを備える。
      - target_date ベースのニュースウィンドウ計算を実装し、datetime.today() 等によるルックアヘッドバイアスを避ける設計。
      - API キーは引数または OPENAI_API_KEY 環境変数から取得（未設定時は ValueError）。
  - ツール
    - tools/paper_verification_report.py:
      - Paper Trading 用検証レポート生成スクリプトを追加（CLI）。期間指定（--from / --to）や DB パス指定（--db）が可能。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値（稼働率>=99%、成功率>=90%、送信率>=95%、P95<=200ms）で PASS/FAIL を判定。
      - DB が存在しない、テーブルが未作成の場合のフォールバック処理（OperationalError を捕捉して N/A 扱い）を実装。
  - ユーティリティ
    - utils.process_priority:
      - Windows / POSIX（Linux / Darwin / FreeBSD）間の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。psutil を利用し、対応不可や権限不足時には警告を出してスキップ。
      - set_cpu_affinity 関数を提供し、最初の N コアにプロセスをピンニングできる（引数 None なら設定しない）。権限不足や未対応環境では警告を出してスキップ。
  - パッケージ情報
    - パッケージの初期バージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Known issues / TODO
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価されてブロックが外れる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨をコメントで記載。
- position_sizing: 将来的に銘柄別単元（lot_size）をサポートするための TODO コメントあり（現状は全銘柄共通の lot_size を想定）。
- utils.process_priority: 未対応 OS や権限不足時は設定をスキップして警告する挙動。運用環境での動作確認を推奨。
- ai.news_nlp: OpenAI API のレスポンス形式に依存するため、外部 API の仕様変更に注意。部分失敗時の既存スコア保護（コード絞り込み DELETE→INSERT）を行うが、ネットワーク断や長期の API 停止シナリオでは運用上の対策が必要。

Environment variables (主要)
- KABUSYS_ENV (development | paper_trading | live)
- MONITOR_POLL_INTERVAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD
- OPENAI_API_KEY
- PAPER_FILL_MODE (instant | partial | never | reject)
- PAPER_TRADING_SQLITE_PATH
- SQLITE_PATH, DUCKDB_PATH
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
- LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

License
- （プロジェクトのライセンス情報はリポジトリの LICENSE ファイルを参照してください）