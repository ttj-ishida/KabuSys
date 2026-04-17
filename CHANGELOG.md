# Changelog

すべての項目は Keep a Changelog 準拠で記載しています。  
リリースは semantic versioning に従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。KabuSys のコア機能（設定管理、実行・監視起動スクリプト、ポートフォリオ構築、リサーチ、ニュース NLP、ユーティリティ、検証ツールなど）を含みます。

### Added
- 基本情報
  - パッケージバージョンを追加: kabusys.__version__ = "0.1.0"。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local の読み込みルール:
    - OS 環境変数を優先（既存キーは上書きしない）。
    - .env.local は .env の上書き用（override=True）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの値ではインラインコメント扱いのルールを実装。
  - Settings クラスを追加し、アプリケーション設定を環境変数経由で提供。
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - PAPER_FILL_MODE（instant|partial|never|reject）等のバリデーションを実装
    - 環境判定プロパティ: is_live/is_paper/is_dev
    - 監視・閾値関連設定: pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値等

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視は本番 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - プロセス優先度を起動時に "high" に設定（utils の set_process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、MockBrokerClient を経由して paper_trading DB（data/paper_trading.db）へ記録することで本番 DB と分離。
    - エンジンは別スレッドで run_session を実行、停止フラグ（data/stop_requested.flag）検知時に安全停止を行う。
    - PID ファイル path（data/execution.pid）をサポート。
    - 起動時にプロセス優先度を "high" に設定。

- 実行系（execution）関連（起動時組み立て）
  - ブローカーファクトリ（BrokerClientFactory）から Broker クライアントを生成するフローを利用。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成。
  - RiskManager のデフォルトコンフィグを追加（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 など）。initial_portfolio_value は broker.get_available_cash() で取得。

- 監視 DB 初期化ユーティリティ呼び出し
  - init_monitoring_db を起動時に呼び出して監視用テーブルが存在することを保証（冪等）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルを score 降順、同点時は signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア正規化（スコア合計が 0 の場合は等金額にフォールバックし警告）。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が上限を超えている場合、新規候補を除外（unknown セクターは除外対象外）。当日売却予定銘柄を除外してエクスポージャー計算可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3。未知は 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき株数を決定。単元株丸め（lot_size, デフォルト 100）や per-stock 上限、aggregate cap（available_cash）を実装。cost_buffer による手数料・スリッページの保守的見積り、およびスケールダウンと残差処理のロジックを実装。
    - risk_based 方式では risk_pct と stop_loss_pct を用いた計算を行う。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（target_date 以前の最新財務データを採用）。
    - 実装は DuckDB を利用して SQL ウィンドウ関数で効率的に計算。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションを実施（1..252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。有効レコードが 3 未満なら None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）や各カラムの統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は data.stats から取り込み）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news テーブルを OpenAI API（デフォルト model: gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込む処理を実装。
  - 機能:
    - ニュース収集ウィンドウを JST 基準で計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 記事を銘柄ごとに集約し、1 銘柄あたり上限記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズ 20 銘柄で API に送信、JSON Mode を期待。
    - 429 / network / timeout / 5xx に対する指数バックオフリトライを実装（最大リトライ回数 _MAX_RETRIES）。
    - レスポンス検証（必須キー検査・型検証・既知コード検査・スコア数値化）。
    - スコアは ±1.0 にクリップして保存。
    - 部分失敗時でも既存スコアを保護するため、対象コードを絞って DELETE→INSERT を行う設計。
  - OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加。usage: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標と閾値:
      - 稼働率（uptime）閾値 99.0%
      - 注文成立率（fill_rate）閾値 90.0%
      - 送信率（send_rate）閾値 95.0%
      - P95 レイテンシ閾値 200 ms
    - P95 計算、日付フィルタ、各テーブル（system_status, trade_logs, risk_logs）を参照した集計・判定・整形出力を実装。

- ユーティリティ（kabusys.utils）
  - process_priority
    - set_process_priority(level) を実装（Windows と POSIX の差分を吸収）。未対応 OS ではスキップして警告。
    - set_cpu_affinity(cpu_count) を実装（指定コア数にプロセスをピン留め、権限や未対応環境では警告してスキップ）。
    - 実行時の例外（AccessDenied 等）は警告として扱い処理継続。
  - utils パッケージと __init__ を追加。

### Changed
- （初回リリースのため過去版との互換性変更はなし）

### Fixed
- 設定・入力の堅牢化:
  - MONITOR_POLL_INTERVAL の不正値処理（0 以下や非整数は警告してデフォルトにフォールバック）。
  - Settings における各種値のバリデーション（env, log_level, PAPER_FILL_MODE 等）。

### Notes / Known limitations / TODO
- apply_sector_cap: price_map に欠損（price == 0.0）がある場合、エクスポージャーが過少見積りされてしまう旨の TODO コメントあり（将来的に前日終値などのフォールバックを検討）。
- position_sizing: lot_size は現状グローバル（全銘柄共通）。将来的に銘柄別単位対応を検討する TODO。
- DuckDB に対する executemany のパラメータが空の場合の注意（AI モジュール内コメント）。部分的失敗を想定した書き込み保護は実装しているが、周辺のエラーケースに注意。
- news_nlp モジュールは外部 API（OpenAI）に依存するため API 利用料金・レート制限に注意。
- run_monitoring は監視用に本番 sqlite_path を常に使用する設計のため、開発環境での運用時は DB 取り扱いに注意。

### Security
- OpenAI API キー等の機密情報は環境変数で扱うことを推奨（Settings で要求・参照）。
- .env 自動読み込み時に OS 環境変数を protected として上書きを回避する仕組みを採用。

---

今後の予定（例）
- 単体テスト・統合テストの追加（特に DuckDB / OpenAI 周り）。
- セクターエクスポージャー計算の価格フォールバック強化。
- 銘柄別 lot_size 対応、手数料モデルの導入。