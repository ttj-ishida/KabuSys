CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in
[SemVer](https://semver.org/) format.

[0.1.0] - 2026-04-16
-------------------

Added
- 初期リリース。
- アプリケーション設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - export 付き行、クォート・エスケープ、行内コメントのパースに対応した .env パーサー実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスでキー単位にプロパティを提供（J-Quants / kabu API / LINE / DBパス / 監視閾値 / 環境判定など）。
  - PAPER_FILL_MODE のバリデーション、paper_trading 用 SQLite パス、PID / kill フラグ等の設定プロパティを実装。

- 実行エントリスクリプト
  - 実行エンジン起動スクリプト run_execution (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を用い、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - data/execution.pid に PID を書く設定（Engine に渡す）。
    - data/stop_requested.flag を検知して安全に停止。
    - スレッドでエンジンを実行し、停止時に join で待機。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期 portfolio value は broker.get_available_cash() を使用。

  - 監視ループ起動スクリプト run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor の check_once を定期実行するポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関係なく production sqlite_path を使用して監視 DB を初期化。
    - stop flag (data/stop_requested.flag) による優雅な停止。
    - DuckDB 接続サポート（duckdb_path）。

- 監視 DB 初期化ユーティリティ (src/kabusys/monitoring/monitoring_db.py は呼び出し元に存在)
  - run_* スクリプトで init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。

- プロセス管理ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) で Windows / POSIX の差分を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) による CPU ピンニング補助。
  - 対応 OS 判定と権限不足時の警告ハンドリングを実装。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソート、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み化、全スコアが 0 の場合は等分にフォールバック。
  - risk_adjustment
    - apply_sector_cap: 同一セクター集中度が上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
    - ロギングとデバッグ出力を含む。
  - position_sizing
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下上限（max_utilization）、コストバッファを考慮した aggregate cap のスケーリング処理。
    - aggregate スケールダウン後の残余配分ロジック（lot 単位で fractional 残差に基づき配分）。
    - price 欠損時のスキップ、lot_size 将来的拡張の TODO コメントあり。

- リサーチ / ファクター計算モジュール (src/kabusys/research/)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（報告日以前の最新財務レコードを選択）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで計算（horizons のバリデーションあり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装、データ不足時は None を返す。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
  - コマンドラインから paper_trading DB を解析して検証レポート生成。
  - 指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), API レイテンシ (avg/max/P95)。
  - デフォルト閾値（稼働率>=99%、成功率>=90%、送信率>=95%、P95<=200ms）を定義し PASS/FAIL を判定。
  - --from / --to / --db CLI 引数をサポート。PAPER_TRADING_SQLITE_PATH 環境変数と連動。

- ニュース NLP スコアリング設計と実装（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を銘柄別に集約して OpenAI (gpt-4o-mini) でセンチメントを算出し ai_scores に書き込む処理フローを実装。
  - バッチ処理（最大 20 銘柄/回）、トークン肥大対策（記事・文字数トリム）、リトライ(429/ネットワーク/5xx) 用の指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードに限定した DELETE/INSERT）などを設計。
  - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC 変換して DB 比較）を算出する calc_news_window を実装。
  - OpenAI API キー未設定時は ValueError を送出。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations / TODOs
- position_sizing.calc_position_sizes:
  - price が欠損 (0.0) の場合にエクスポージャーが過少見積もられる旨の TODO がある。前日終値等でのフォールバック検討がコメントされている。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応 OS の場合は警告を出してスキップする安全策を実装。
- news_nlp:
  - 大きな処理フローと堅牢化（バッチ、リトライ、検証）設計を実装しているが、実稼働でのパラメータ調整や API コスト管理が必要。
- run_monitoring:
  - 監視は KABUSYS_ENV にかかわらず production sqlite_path を使用する（意図的な設計：監視は本番 DB を参照）。
- .env パーサーは多くのケースを扱うが、極端な edge-case の出力は注意が必要（特殊なエスケープや改行を含む値など）。

環境変数の主なデフォルトと注目点
- KABUSYS_ENV: development / paper_trading / live（不正値はエラー）
- SQLITE_PATH: data/monitoring.db（監視用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"、不正値は例外）
- OPENAI_API_KEY: news_nlp の API キー

もしリリースノートに追加してほしい点（例: 日付の調整、より細かいファイル単位の変更履歴、既知のバグ追跡番号など）があれば指示してください。