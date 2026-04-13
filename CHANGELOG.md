CHANGELOG
=========

すべての注目すべき変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Initial release — 基本機能の実装・エクスポート

Added
- パッケージ基盤
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
  - モジュールの公開 API を __all__ で整理（portfolio / research 等のエクスポート）

- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時には MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）に隔離してログを取る設計
    - プロセス優先度を起動時に "high" に設定
    - DuckDB 接続を受け取り ExecutionEngine を構成してセッション実行
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データの恒久保存）
    - init_monitoring_db による監視テーブル初期化・DuckDB 接続の利用、プロセス優先度設定、例外保護を含むループ制御

- 設定管理
  - config.Settings を実装
    - .env / .env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env パースの強化（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）
    - 環境変数の保護（OS 環境変数を protected として上書きを制御）
    - 各種プロパティ: J-Quants / kabu API トークン、duckdb/sqlite パス、paper_trading 用パス、pid/kill flag パス、各種閾値、env/log_level 検証等
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 (タイブレークは signal_rank) で候補選定
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコアが 0 の場合は等分にフォールバックし WARNING 出力）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づく候補除外（"unknown" セクターは上限適用しない）
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマッピングとフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score に基づいた株数計算
      - lot_size（単元）で丸め、最大ポジション比率や max_utilization、cost_buffer（手数料・スリッページ見積）を考慮した aggregate cap を実装
      - available_cash を超過する場合のスケーリングと端数のロット再配分アルゴリズムを実装

- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離の計算（window バッファ有り、データ不足時は None）
    - calc_volatility: ATR20・相対 ATR・20日平均売買代金・出来高比率など
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算
  - research.feature_exploration
    - calc_forward_returns: 指定 horizon の将来リターンを一括計算（horizons の検証あり）
    - calc_ic: スピアマンランク相関（IC）計算、データ不足時は None
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ
  - research パッケージの __init__ で必要関数をエクスポート（zscore_normalize を含む）

- AI ニューススコアリング
  - ai.news_nlp
    - calc_news_window: JST に基づくニュース集計ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST に対応）
    - score_news: OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリングの実装（バッチ送信、最大銘柄数、文字数制限、リトライ / バックオフ、レスポンス検証、スコアクリッピング、DuckDB テーブルへの安全な書き込み方針）
    - 設計方針: ルックアヘッドバイアス回避のため date を引数で受け取る、API キーの明示的指定または環境変数参照（未設定時は ValueError）

- 監視・検証ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポートの CLI 実装（--from / --to / --db）
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数などを集計・判定するレポートを標準出力へ出力
    - しきい値（稼働率 99%、成立率 90% 等）を定義して PASS/FAIL 判定を行う

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows/Linux/macOS 等を吸収してプロセス優先度を設定（psutil 利用、アクセス拒否をログでスキップ）
    - set_cpu_affinity(cpu_count): 最初の N コアへピン留め。引数検証と例外ハンドリングあり

Changed
- （初版のため特定の「変更」はなし）

Fixed
- （初版のため修正履歴はなし）

Security
- OpenAI API キー等の機密値は環境変数から取得する設計。Settings は .env 自動ロード機能を持つが、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Notes / Known limitations / TODO
- position_sizing.calc_position_sizes: price が欠損（0.0）の場合にエクスポージャー過小評価となる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する想定。
- DuckDB の executemany や空パラメータに関する挙動についてコメントがあり、部分失敗時の保護処理（コードを限定して DELETE→INSERT）が採用されている。
- ai.news_nlp.score_news は API レスポンスのバリデーションやリトライを実装しているが、API 使用に伴う料金やレート制限には注意が必要。
- run_monitoring は監視用 DB として常に sqlite_path（本番）を参照するため、paper_trading 環境下でも監視は本番 DB を参照する点に注意。

Compatibility / Breaking Changes
- 初版リリースのため破壊的変更の記載なし。将来のマイナーバージョンで設定名や挙動が変更される可能性あり（特に環境変数名と .env の自動ロード挙動）。

環境変数の主な一覧（デフォルト / 重要項目）
- KABUSYS_ENV (development|paper_trading|live) — 実行環境
- SQLITE_PATH (data/monitoring.db), PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- DUCKDB_PATH (data/kabusys.duckdb)
- PID_FILE_PATH (data/execution.pid), KILL_FLAG_PATH (data/kill.flag)
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE (instant|partial|never|reject)
- OPENAI_API_KEY — ai.news_nlp で利用

---

詳細な実装や設計意図はソースコード内 docstring / コメントに記載しています。補足の変更履歴や差分の粒度調整が必要であれば、特定のファイルや機能ごとに分けた changelog エントリを作成します。どの粒度がよいか教えてください。