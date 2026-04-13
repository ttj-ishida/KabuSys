# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - 環境に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用するオプションを実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを行う。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - 監視用テーブル生成（init_monitoring_db）を起動時に冪等的に保証。
    - duckdb を併用（duckdb_path に接続）。

  - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出す。
    - 監視（monitoring）は実行環境にかかわらず本番 sqlite_path を参照する設計。
    - 起動時にプロセス優先度を設定し、SQLite / DuckDB 接続を確立して SystemMonitor.check_once() を定期実行する（例外はログに出して継続）。
    - KeyboardInterrupt をハンドルしてクリーンに終了。

- 環境・設定管理
  - config.py: .env/.env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。  
    - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env の行パーサは export 形式、クォート、エスケープ、インラインコメントに対応。
    - Settings クラスを提供し、各種環境変数をプロパティとして取得（検証付き）。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須変数チェック
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH などのパス
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）
      - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を明確化）
      - kill_flag 関連・閾値設定（CPU/MEM/DISK）

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等配分へフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づいて新規候補を除外。既存保有の時価に基づく計算、"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは警告し 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: weight / candidates / 各種制約（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）に基づいて発注株数を計算。
    - risk_based と equal/score の両方式をサポート。単元株（lot_size）丸め、aggregate cap によるスケーリングと端数配分ロジックを実装。
    - 価格欠損時のスキップ、portfolio_value <= 0 の早期リターンなど堅牢性向上。

- リサーチ／ファクター計算
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials を用いて各種ファクター（モメンタム、ATR、平均売買代金、PER/ROE 等）を計算。データ不足時は None を返す設計。
    - SQL ウィンドウ関数を活用し、必要行数が不足する場合の条件付与を行う。
  - research.feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン先の将来リターンを一括取得（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - factor_summary / rank: 基本統計量（count/mean/std/min/max/median）とランク算出ユーティリティを追加。
    - pandas 等に依存せず標準ライブラリのみで実装。

- AI ニューススコアリング
  - ai.news_nlp:
    - raw_news, news_symbols を集約し OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を算出し ai_scores テーブルへ書き込むロジックを追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算ユーティリティを実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、トークン対策（記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護する安全な DB 書き込み（該当コードのみ DELETE→INSERT）などを実装。
    - OpenAI API キーが未設定の場合は ValueError を返す。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成ツールを追加。CLI で期間指定可能（--from, --to）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を計算し閾値（稼働率 99% など）で PASS/FAIL を判定。
    - P95 計算、日付フィルタの組立、DB 不存在やテーブル未作成時の安全ハンドリングを実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を追加。Windows と POSIX 系（Linux/Mac/FreeBSD）を抽象化してプロセス優先度を設定。権限不足等は警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加。最初の N コアに固定する機能（利用可能コア数より大きければ全コア利用へフォールバック）。不正引数は ValueError。

- DuckDB / SQLite の併用
  - 多くのモジュール（research, ai, 実行・監視スクリプト等）が duckdb 接続を受け取り、ローカルデータ（prices_daily, raw_financials, raw_news 等）を参照する設計を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの扱いは引数または環境変数（OPENAI_API_KEY）を明示的に要求し、未設定時は例外を出す実装。

---

注記:
- 多くのモジュールは「外部 API への直接アクセスを行わない」「DB 参照は DuckDB / SQLite に限定」「副作用を最小化する」などの設計方針に基づいて実装されています。  
- 実装上の細かい挙動（例: PAPER_FILL_MODE の許容値、MONITOR_POLL_INTERVAL の不正値フォールバック、セクター unknown の扱い、価格欠損時のスキップ等）はソース内コメント・ドキュメントに明記されています。必要であれば各モジュールごとの詳細な変更点や使用方法のドキュメントを追記します。