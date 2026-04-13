# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、提示されたソースコードから推測して作成した初期リリース向けの変更履歴です。

なおバージョン番号はパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせています。

## [0.1.0] - 2026-04-13
初回リリース。

### 追加
- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 実行を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB と SQLite の接続管理（起動/終了時にクローズ）を行う。
    - RiskConfig のデフォルトパラメータを定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に格納）。
    - 起動時にプロセス優先度を "high" に設定、例外発生時はログを出力して次のポーリングへ継続、KeyboardInterrupt で優雅に終了。

- 設定管理モジュールを追加/強化（config.py）
  - .env ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local の読み込み順序と既存 OS 環境変数の保護を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮して堅牢に実装。
  - Settings クラスを提供（各種環境変数をプロパティとして取得・検証）。
    - データベースパス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
    - PID / Kill flag パス
    - 閾値設定 (CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT)
    - 環境種別 KABUSYS_ENV の検証（development, paper_trading, live）
    - PAPER_FILL_MODE の検証（instant, partial, never, reject）
    - LOG_LEVEL の検証 等

- 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）を各起動スクリプトで呼び出すことで監視テーブル存在を保証（冪等）。

- portfolio モジュール（銘柄選定・重み付け・リスク調整・株数計算）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・signal_rank をタイブレークにして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重（スコア全体が 0 の場合は等金額にフォールバックし warning を出力）。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未定義レジームは警告のうえ 1.0 を返す）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。
    - risk_based: リスク (%), stop_loss_pct に基づく株数算出。
    - equal/score: weight に基づく配分、per-position 上限・aggregate cap（available_cash）でスケーリング。
    - 単元株丸め（lot_size、デフォルト 100）や cost_buffer を用いた保守的コスト試算。
    - aggregate cap 超過時はスケールダウンと lot 単位での余り配分アルゴリズムを実装。

- research モジュール（DuckDB を用いたファクター計算 & 解析）
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日未満は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR は NULL 伝播を正しく扱う）。
    - calc_value: raw_financials から最新財務を取って PER / ROE を計算。
    - SQL ベースで DuckDB を活用し、営業日ウィンドウのバッファを考慮した実装。
  - feature_exploration.py
    - calc_forward_returns: target_date から将来リターン（複数ホライズン）を一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクで扱う安定ランク変換。
    - factor_summary: count/mean/std/min/max/median 等の統計要約を提供。
  - research.__init__ で zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI / ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI API（デフォルト gpt-4o-mini）を用いてニュースセンチメントを -1.0〜1.0 にスコアリング。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して扱う。
    - 1 銘柄あたりの最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチサイズ（最大 20 銘柄）で API を送信し、429/ネットワーク/5xx 等は指数バックオフでリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ、成功分のみ ai_scores テーブルへ置換挿入。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX (Linux, Darwin, FreeBSD) を吸収してプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを先頭 N コアに固定。引数検証・権限例外処理を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート出力スクリプト（コマンドライン）。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等の指標を SQLite（paper_trading.db）から集計し、閾値に基づく PASS/FAIL 判定を出力。
    - p95 計算、日付フィルタ、DB 存在チェック、SQL の OperationalError に対するフォールバックを実装。
  - tools パッケージの __init__ を追加。

- パッケージメタ
  - kabusys.__init__ に __version__ = "0.1.0" を設定。
  - portfolio / research / utils 等のパッケージ公開 API を __all__ で整備。

### 変更（設計上の注意・挙動）
- デフォルトの DB/ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）を参照するが、不正値はログ警告のうえ 60 秒にフォールバックする。
- run_execution は Paper Trading 実行時に paper_trading DB を使用し、本番 DB と完全に分離するよう設計されている。
- config の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の安全性を配慮）。
- research の SQL 実装は DuckDB を前提としており、prices_daily / raw_financials テーブルの存在を前提とする。

### 既知の制限・TODO（ソースコードコメントに基づく）
- apply_sector_cap: price_map に price が欠損 (0.0) の場合、エクスポージャーが過小評価される可能性があり、将来的には前日終値や取得原価等のフォールバックを検討する旨の TODO がある。
- position_sizing: 将来的に銘柄別 lot_size を持たせる設計変更を検討中（現在はグローバル lot_size 引数を使用）。
- ai/news_nlp の実装は堅牢性を考慮しているが、外部 API を使うため実環境では API レート制限や課金に注意が必要。
- run_monitoring: 監視処理は常に本番 sqlite_path を参照する設計のため、監視データを分離したい場合は実装の調整が必要。

### セキュリティ
- OpenAI API キーは明示的に必要（api_key 引数または OPENAI_API_KEY 環境変数）。未設定時は処理が失敗しないよう ValueError を投げる実装になっている。

### 修正（バグ修正）
- （初回リリースのため過去の修正は無し。実装内での多くのエラーハンドリングとフォールバックが組み込まれていることを明記。）

---

今後のリリース案（推奨）
- Unreleased: 単体テスト追加、CI/CD ワークフロー、DuckDB/SQLite のマイグレーションスクリプト、AI モジュールのエンドツーエンドテスト。
- 次バージョン: リスク管理パラメータの外部化、lot_size の銘柄別サポート、監視の DB 分離設定オプション追加。