# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
- 開発中の変更や小さな修正をここに記載してください。

---

## [0.1.0] - 2026-04-13
最初の公開リリース。本リポジトリに含まれる主要な機能と実装をまとめます。

### Added
- 基本パッケージとメタ情報
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。

- 環境設定・.env 自動読み込み（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env ファイルのパーサは export 形式、クォートやバックスラッシュエスケープ、インラインコメントを正しく処理。
  - Settings クラスを導入し、環境変数からアプリケーション設定値を安全に取得（必須チェック、型変換、値検証を含む）。
  - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値 (CPU/MEM/DISK), KABUSYS_ENV, LOG_LEVEL など。
  - KABUSYS_ENV の有効値検証（development, paper_trading, live）を実装。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB (デフォルト data/paper_trading.db) を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとセッション実行を行う。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB 接続も併用（duckdb_path）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）。無効な値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を提供し、Windows と POSIX 系（Linux/Mac/FreeBSD）での優先度(nice/HIGH_PRIORITY_CLASS) を抽象化して設定。
  - set_cpu_affinity(cpu_count) を追加し、指定コア数への CPU affinity 固定をサポート（アクセス権限や未対応プラットフォームではスキップして警告）。
  - 権限不足や未実装 API の例外を安全にハンドリング。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定と重み計算
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分（スコアが全て 0 の場合は等分にフォールバック）。
  - risk_adjustment: セクター集中制限・レジーム乗数
    - apply_sector_cap: 既存保有のセクター比率を計算し、max_sector_pct 超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数を返却（bull/neutral/bear に対応、未定義値はフォールバックして警告）。
  - position_sizing: 株数算出・リスク制限・単元丸め
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。stop_loss、risk_pct、max_position_pct、max_utilization、lot_size、cost_buffer を考慮して買付株数を算出。aggregate cap を考慮したスケーリングと端数処理を実装。

- リサーチ・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を DuckDB の prices_daily に対して計算。
    - calc_volatility: 20日 ATR、ATR/株価、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近の財務データを取得し PER, ROE を計算（EPS=0 の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）を取得。ホライズン検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（欠損・非数値を排除、サンプル数が少ない場合は None）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティを提供。
  - zscore_normalize を data.stats から再エクスポート（research パッケージの一部として利用可能）。

- ニュース NLP モジュール（kabusys.ai.news_nlp）
  - raw_news を OpenAI API（gpt-4o-mini を想定）で銘柄別にセンチメント化し、ai_scores テーブルへ書き込む処理を実装。
  - チャンク処理（1 API コールあたり最大 20 銘柄）、記事数・文字数制限（銘柄ごとに最大記事数・最大文字数）によるトークン肥大化対策を実装。
  - リトライロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を導入。
  - API レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 書き込み戦略（該当銘柄のみ置換）などのフェイルセーフ設計。
  - calc_news_window を導入し、JST ベースのニュース集計ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換して利用。

- Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
  - paper_trading 用 SQLite DB（デフォルト data/paper_trading.db）から集計を行い、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出する CLI レポートを追加。
  - 判定基準（閾値）を定義して PASS/FAIL を出力。
  - SQL の日付フィルタリング、P95 計算、N/A 表示処理などを実装。
  - コマンドライン引数 --from/--to/--db をサポート。

- DB 初期化ユーティリティ
  - monitoring 用のテーブル存在保証関数 init_monitoring_db を参照（run スクリプトで冪等に呼び出して監視テーブル作成を保証）。

### Changed
- （初回リリースのため該当なし。今後のリリースで差分を記載してください）

### Fixed
- （初回リリースのため該当なし。バグ修正は次バージョンで記載してください）

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得する設計。未設定時は明示的にエラーを返す。

### Notes / Implementation details
- DuckDB と SQLite を併用する設計:
  - SQLite は監視 / 発注ログなどの運用データに想定。
  - DuckDB は価格・財務データなどの解析ワークロード向けに使用。
- Paper Trading 環境は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH により上書き可能。PAPER_FILL_MODE によるモック約定動作の設定をサポート。
- 各モジュールは外部 API（ブローカー・LINE 等）への直接呼び出しを最小化し、リサーチ／シグナル生成部分は本番発注系にアクセスしない方針で実装。
- ログレベルや各種閾値は環境変数で調整可能。Settings クラスによりバリデーションが行われる。

---

開発・運用に伴う補足情報や既知の制約は README やドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。変更履歴は今後のコミットで更新していきます。