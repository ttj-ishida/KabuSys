CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).

Unreleased
----------

- （無し）

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初回公開リリース。パッケージバージョンは __version__ = "0.1.0"。
  - DuckDB / SQLite ベースのデータ処理と、本番／Paper Trading の DB 分離を前提にした実行フローを実装。

- エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用して起動。
    - プロセス優先度を "high" に設定してから実行。
    - sqlite3 / duckdb 接続を確立し、監視用 DB の初期化（init_monitoring_db）を行う。

  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は Paper 用 SQLite（デフォルト data/paper_trading.db）を使用し本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine.run_session 呼び出しを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機能を提供（プロジェクトルートは .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / PID/KILL フラグ /監視閾値 / PAPER_TRADING 関連設定等をプロパティで提供。入力値の検証を行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - settings インスタンスをモジュールレベルで提供。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定 (set_process_priority) と CPU affinity 固定 (set_cpu_affinity) を提供。
    - psutil を使用。権限不足や未対応環境では警告を出してスキップするフェイルセーフ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - 全スコアが 0 の場合は等金額配分へフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中チェック (apply_sector_cap)：既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数 (calc_regime_multiplier)："bull"/"neutral"/"bear" に基づく乗数を返却。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - position sizing 実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株数（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）を考慮したスケールダウン、端数処理（残差に基づく追加配分）を実装。
    - cost_buffer による保守的コスト見積をサポート。

- リサーチ（ファクター計算・探索）
  - research/factor_research.py
    - DuckDB を使ったモメンタム、ボラティリティ、バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials テーブルのみ参照し、欠損データに対する安全な処理を実装。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結。

  - research/__init__.py
    - 公開 API にファクター計算群と zscore_normalize をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini、JSON Mode）へ送り、銘柄ごとのセンチメント ai_score を ai_scores に書き込む処理を実装。
    - 前日15:00 JST〜当日08:30 JST のニュースウィンドウを計算（calc_news_window）。
    - 銘柄当たり記事数・文字数のトリム、最大 20 銘柄/チャンクで API 送信、429/ネットワーク/5xx に対する指数バックオフでのリトライ実装、レスポンスの厳密な JSON 検証、スコア ±1.0 のクリップ、部分失敗時に既存スコアを保護するための部分置換（DELETE where date=? and code=ANY(codes) → INSERT）などの堅牢化。
    - OPENAI_API_KEY 必須（未設定時は ValueError を発生）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装。--from/--to/--db オプション対応。
    - 稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタを ISO8601 UTC 文字列で組み立て、DB テーブル未存在時を安全に扱う（OperationalError を捕捉して N/A を返す）。

Changed
- （初回リリースのため該当なし）

Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出し、警告の上デフォルト値へフォールバックするバリデーションを追加。

Security
- OPENAI_API_KEY は必須。ai/news_nlp の score_news() は API キー未設定時に ValueError を送出して処理を停止する。

Notes / Known limitations
- DuckDB の executemany に関する制約（バージョン依存）に注意している箇所がある（ai/news_nlp の DB 書き込み時の扱い）。
- position_sizing の price 欠損（0.0）時は TODO コメントがあり、将来的に前日終値や取得原価でのフォールバックを検討。
- process priority / cpu affinity の設定は権限不足や未対応 OS ではスキップされる（警告ログ）。
- Paper Trading の振る舞いは環境変数と専用 DB（PAPER_TRADING_SQLITE_PATH）で完全に分離される設計。
- 一部の閾値やデフォルト値（例: RiskManager の config 等）はコード内でハードコードされており、将来的に外部設定化が想定される。

Acknowledgements
- psutil、duckdb、openai 等の OSS ライブラリに依存しています。