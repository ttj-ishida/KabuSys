CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しており、本リポジトリの現状（初回リリース相当）をコードベースから推測して記載しています。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本情報
  - パッケージバージョンを追加: kabusys.__version__ == "0.1.0"。
  - パッケージ公開向けに主要コンポーネントをモジュール化（data, strategy, execution, monitoring を __all__ に追加）。

- 実行エントリ / デーモン系
  - run_monitoring.py
    - SystemMonitor を用いたポーリング監視ループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込む（utils.process_priority を利用）。
    - 停止用フラグファイル data/stop_requested.flag を監視して安全にループを終了。

  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を統合 (実運用/モック切替)。
    - Engine 停止/起動のための PID ファイル（data/execution.pid）および停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数処理
  - kabusys.config.Settings を追加し、アプリケーション設定を環境変数から取得する API を提供。
  - .env / .env.local の自動ロード機能を追加（OS 環境変数が優先。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの扱い、無効行のスキップ等に対応。
  - 各種設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（instant|partial|never|reject の検証）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU/MEM/DISK 閾値（パーセンテージ）
    - KABUSYS_ENV 検証（development|paper_trading|live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- モニタリング DB 初期化
  - init_monitoring_db を利用して監視テーブルの冪等な初期化処理を各起動スクリプトから呼び出すように統合（sqlite3 を使用）。

- 実行系コンポーネント（Execution サブパッケージ）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の組み立てを run_execution で実施。
  - RiskManager のデフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。initial_portfolio_value は broker.get_available_cash() によって初期化。

- ツール
  - tools/paper_verification_report.py を追加:
    - Paper Trading の検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを SQLite のテーブル（system_status, trade_logs, risk_logs など）から集計。
    - 判定基準（しきい値）を定数化:
      - 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from, --to）と --db オプションに対応。DB が存在しない場合のエラーメッセージを実装。

- ポートフォリオ構築（portfolio パッケージ）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を実装（score 合計が 0 の場合は等配分にフォールバックし WARNING を出力）。

  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限のチェック（売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは制限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は警告の上 1.0 にフォールバック）。

  - position_sizing.py
    - calc_position_sizes: 等配分 / スコア加重 / リスクベースの株数決定を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・合計の aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮、残差配分ロジックを実装。
    - price 欠損時のスキップやデバッグログを整備。
    - 将来的な拡張に向けた TODO（銘柄別 lot_size 等）を明記。

- リサーチ（research パッケージ）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装（DuckDB 上の prices_daily / raw_financials テーブル参照）。
    - 各種窓長・スキャン範囲（MA200, ATR20 等）を定数化し、ウィンドウ不足時の None ハンドリングを厳密に行う。

  - feature_exploration.py
    - calc_forward_returns: 将来リターンを複数ホライズンで一括取得（SQL で LEAD を利用）。
    - calc_ic: スピアマン（ランク）ベースの IC 計算（結合・欠損排除・有効レコード閾値）。
    - rank / factor_summary: ランク処理（同順位は平均ランク）や基本統計量（count/mean/std/min/max/median）計算を標準ライブラリのみで実装。
  - research.__init__ に主要関数をエクスポート（zscore_normalize も外部から取り込み）。

- AI ニュース NLP（ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理を追加。
  - 特徴:
    - ニュース収集ウィンドウの厳密定義（JST 基準を UTC に変換）。
    - 銘柄ごとの記事トリム（記事数・文字数上限）と最大バッチ 20 銘柄の API 送信。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳格なバリデーション、スコアクリッピング（±1.0）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ユーティリティ（utils）
  - process_priority.py
    - set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）に対応してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
    - set_cpu_affinity(cpu_count) を実装し、最初 N コアにプロセスをピン留めする機能を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
    - 標準的な AccessDenied / AttributeError / NotImplementedError のハンドリングとログ出力を実装。

Changed
- 初回リリースのため該当なし（新規実装群）。

Fixed
- 初回リリースのため該当なし（パーサーや各種関数で多くの入力検証を追加し堅牢化）。

Notes / Usage
- 主要な環境変数（デフォルト含む）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - SQLITE_PATH: デフォルト data/monitoring.db（監視用 DB）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading 時に使用）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - OPENAI_API_KEY: ai/news_nlp 用（必須。score_news 呼び出し時に指定可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 に設定すると .env 自動ロードを無効化

- ファイル / フラグ
  - 停止フラグ: data/stop_requested.flag（run_monitoring / run_execution が存在を監視）
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に使用）
  - paper_verification_report のデフォルト DB: data/paper_trading.db

- 注記 / TODO
  - position_sizing 内で価格欠損時のフォールバック（前日終値や取得原価）を将来検討する旨の TODO を含む。
  - ai/news_nlp は API 呼び出しや DB 書き込みで部分失敗が発生しても他銘柄データの保護を考慮した実装方針を持つ（DELETE→INSERT の限定的更新）。

Security
- 設定関連では秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は環境変数として必須扱い。未設定時は ValueError を送出して早期に検出。

Acknowledgements / Implementation detail
- DuckDB を分析系（prices_daily, raw_financials 等）に使用、sqlite3 は監視・paper_trading データ格納に使用。
- 外部依存: psutil（プロセス優先度/affinity）、duckdb、openai（news_nlp）、sqlite3（標準ライブラリ）など。

-- END --