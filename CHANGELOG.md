CHANGELOG
=========

このプロジェクトの変更履歴は「Keep a Changelog」準拠で記載しています。
リリースや重要な変更点は下記をご参照ください。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------
追加 (Added)
- 基本パッケージ初回リリース。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0

- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と分離（デフォルト: data/paper_trading.db）。
    - ブローカークライアントのファクトリ経由で Broker を生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - プロセス優先度を起動直後に "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値は警告しデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB に記録される設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数管理
  - config.py: 環境変数読み込み/管理モジュールを追加。
    - .env / .env.local の自動ロード機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数。
    - .env 読み込みの上書き挙動（override / protected）を実装。
    - 必須環境変数取得ヘルパー _require()（未設定時は ValueError）。
    - Settings クラスを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境判定など）。
    - 設定値の検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE（有効値制約）。

- 監視・プロセス制御ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定 set_process_priority(level) を実装（Windows / POSIX 対応、権限不足時は警告してスキップ）。
    - プロセスの CPU affinity を固定する set_cpu_affinity(cpu_count) を実装（権限や未対応 OS では警告してスキップ）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア合計0時は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用する候補フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく株数算出、単元株丸め、aggregate cap によるスケールダウン、cost_buffer の考慮等を実装。
  - portfolio/__init__.py で主要関数群をエクスポート（外部使用を意識した API 設計）。

- リサーチ（ファクター・探索）モジュール
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いるファクター計算を実装（移動平均・ATR・リターン・PER/ROE 等）。
    - 各関数は target_date を指定して計算し、(date, code) ベースの辞書リストを返す。
  - research/feature_exploration.py
    - calc_forward_returns: 未来リターン（複数ホライズン）計算（引数検証、範囲バッファ付き）。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、ランクラング処理、基本統計量の算出を標準ライブラリのみで実装。
  - research/__init__.py で zscore_normalize（data.stats 由来含む）や上記関数をエクスポート。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事/文字数トリム、429/5xx/ネットワークエラーへの指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリッピング等を実装。
    - タイムウィンドウ計算（JST ベースで前日 15:00 ～ 当日 08:30 相当の UTC 範囲）を提供する calc_news_window。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI 引数で期間（--from, --to）と DB パス（--db）を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を集計し、PASS/FAIL 判定（閾値はファイル内定数で定義）。
    - DuckDB ではなく paper_trading の SQLite DB を参照する想定。

変更 (Changed)
- 監視/実行の DB 初期化:
  - run_execution.py/run_monitoring.py 内で init_monitoring_db(sqlite_conn) を呼び、監視テーブルの存在を冪等に保証。

修正 (Fixed)
- 環境ファイルパーシングの堅牢化:
  - config._parse_env_line() にて export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、コメント判定ロジック等の実装で .env の多様な記法に対応。

既知の注意点 / マイグレーション
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用」します。監視データを分離したい場合は sqlite_path を変更してください。
- PAPER_FILL_MODE 等の設定に不正な値を与えると Settings プロパティで ValueError が発生します。設定値は .env.example を参照してください。
- set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでは警告を出してスキップします（フェイルセーフ）。
- ai/news_nlp.score_news は OpenAI API キーが必須です。キー未設定時は例外が発生します。
- position_sizing.calc_position_sizes は将来的に銘柄別 lot_size 対応の拡張を想定したコメント（TODO）を含みます。

セキュリティ (Security)
- 本リリースにおけるセキュリティ関連の既知問題はありません。API キー等の秘密情報は .env または環境変数で管理してください。

参考: 環境変数・デフォルトパス（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用デフォルト）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
- OPENAI_API_KEY: AI スコアリング用 API キー

今後の予定（短期）
- portfolio の lot_size を銘柄別に扱う拡張
- ai/news_nlp の部分失敗時の部分ロールバック改善（現在は書き換え対象コードのみ更新する戦略）
- DuckDB/SQLite スキーマのバージョン管理とマイグレーション機構導入

----- 
この CHANGELOG は、現行コードベースの実装内容から推測して作成しています。実際のコミット履歴が存在する場合はそれに合わせて更新してください。