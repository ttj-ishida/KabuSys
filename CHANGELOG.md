# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは「Keep a Changelog」の形式に準拠しています。ソースコードから推測可能な機能追加・仕様・重要挙動を基に初期リリースの変更履歴を作成しています。

※ 日付はソース解析時点（2026-04-12）を使用しています。実際のリリース日やバージョンポリシーに応じて調整してください。

## [Unreleased]
- 現時点では未リリースの変更はありません。

## [0.1.0] - 2026-04-12

### Added
- 基本アーキテクチャと主要コンポーネントの初期実装を追加。
  - パッケージエントリポイント（モジュール）を含む初期リリース。
  - バージョンは `kabusys.__version__ = "0.1.0"`。

- 実行系 / 運用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた DB 切り分け（paper_trading モード時は専用 SQLite を使用）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - duckdb 接続を利用（duckdb_path を使用）。
    - PID ファイルパス設定をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定（set_process_priority を利用）。
    - ループ内の例外をログにキャッチして継続するフォールトトレラント挙動。

- 設定 / 環境変数管理
  - config.Settings クラスを導入。主要設定項目をプロパティとして提供。
    - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順序と override のルール（OS 環境変数は保護）。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - 各種パス・閾値・フラグをプロパティ化（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
    - 環境種別の検証（KABUSYS_ENV: development / paper_trading / live）や LOG_LEVEL の検証。
    - PAPER_FILL_MODE の検証（instant / partial / never / reject）。
    - 便利プロパティ: is_live / is_paper / is_dev。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア順ソート（同点は signal_rank で tiebreak）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計が 0 の場合はフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限の適用（既存保有を考慮、sell_codes を除外可能）。unknown セクターは上限適用除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定。
    - 単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer を考慮したスケーリング、aggregate cap 時のスケールダウンと残差配分ロジックを実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出（true_range の NULL 処理に注意）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（最新の財務データを target_date 以前から取得）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）を DuckDB で一括取得。
    - calc_ic: スピアマンランク相関（IC）計算（rank 関数を使用し同順位は平均ランク）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）。
    - rank: 値からランクへの変換（同順位は平均ランク、丸め処理で ties 回避）。
  - research パッケージは kabusys.data.stats の zscore_normalize を re-export。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）に送信し銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を追加。
    - バッチサイズ、最大記事数、文字数トリム、タイムウィンドウ（JST→UTC 変換）等の制約を設計。
    - リトライ戦略（429 / ネットワーク / 5xx に対する指数バックオフ）やレスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - API キー未指定時は明示的な例外を発生（OPENAI_API_KEY を参照する設計）。

- 運用ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に応じた優先度設定を psutil 経由で実装。アクセス権エラー等はログワーニングでスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン止めするユーティリティを追加（入力検証、例外ハンドリングあり）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポートをコマンドラインで生成するスクリプトを追加。
    - 指標: 稼働率 (uptime), 注文成功率(fill_rate), 送信率(send_rate), P95 レイテンシ 等。
    - デフォルト閾値（PASS/FAIL 判定）を定義（稼働率 >=99%、fill_rate >=90% 等）。
    - DB パスは CLI 引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトを解決。
    - P95 計算、日付フィルタ、テーブル存在不備時のフォールトトレラントなハンドリングを実装。

- DB 周り
  - DuckDB と SQLite を併用する設計を導入。
    - duckdb_path / sqlite_path / paper_sqlite_path のデフォルトパスを設定（data/*.db）。
    - monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの冪等初期化を行う（run_execution, run_monitoring で利用）。

### Changed
- 初期リリースのため、既存コードからの変更履歴はありません（初期機能群の導入）。

### Fixed
- 初期実装における例外耐性・入力検証を強化。
  - MONITOR_POLL_INTERVAL が非整数または 0/負数のときは警告してデフォルト値（60 秒）を使用。
  - Settings の列挙値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を追加し不正値で早期にエラーを出す。
  - DuckDB/SQLite に対するクエリ呼び出し部で OperationalError を捕捉してフォールトトレラントに振る舞う（tools.paper_verification_report など）。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要がある旨を明示。未設定時は ValueError を送出して明示的に失敗する。

### Notes / Important behaviour
- Paper Trading（KABUSYS_ENV=paper_trading）は本番の SQLite DB と完全分離（デフォルト: data/paper_trading.db）。実運用での誤操作を防止する設計。
- 監視（run_monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path を使用する点に注意。監視用 DB を別にしたい場合は設定を調整する必要あり。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。また KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを抑制可能。
- process_priority / cpu_affinity 設定は権限不足や未対応プラットフォームでスキップされる（警告のみ）。
- 一部処理は DuckDB の SQL ウィンドウ関数（OVER, LAG, LEAD, ROW_NUMBER など）に依存しているため、DuckDB 接続とテーブルスキーマの準備が前提。

---

この CHANGELOG はソースコードから推測して作成したものです。実際のリリース管理や変更点の確定には、コミット履歴やリリースノートの正式な記録に基づいて調整してください。