# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
セマンティックバージョニング (SemVer) を採用しています。

## [Unreleased]

- 検討中 / 未完了
  - ai/news_nlp モジュール: OpenAI API 周りの処理設計（バッチング、リトライ、レスポンス検証など）は大枠を実装済みですが、記事取得関数（_fetch_articles 相当）がスニペットで切れており、部分的に未完成です。API 呼び出しの完全な統合・例外ハンドリングの追加検証が必要です。
  - portfolio.position_sizing: 価格欠損時のフォールバック（前日終値・取得原価等）について TODO コメントあり。実運用時は欠損価格の扱いを明確化することを推奨します。
  - DuckDB への大量書き込み時の安全弁（executemany の事前チェック等）は注意喚起コメントあり。部分的失敗ケースのリカバリ設計を検討中。

---

## [0.1.0] - 2026-04-16

初回リリース相当。以下の主要機能を実装しています。

### Added（追加）
- 基本構成
  - パッケージ初期化とバージョン定義を追加（kabusys.__init__.__version__ = "0.1.0"）。

- 設定管理（kabusys.config）
  - 環境変数・.env ファイル自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込む。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートなしで直前が空白ならコメントとして扱う）
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）機構を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティを提供（DB パス、PID ファイル、閾値、環境判定メソッドなど）。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。
  - PAPER_TRADING_SQLITE_PATH を使った paper_trading 用 DB パス取得を追加。

- 実行エンジン起動スクリプト（run_execution.py）
  - ExecutionEngine 起動スクリプトを実装。
  - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite DB を使用し、本番 DB と完全分離。
  - BrokerClientFactory によるブローカークライアント生成と、それを使った OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを追加。
  - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、available_cash を初期ポートフォリオ値として取得するロジックを追加。
  - 実行はスレッドでデーモン実行し、data/stop_requested.flag による外部停止フラグで安全に停止可能。
  - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。

- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを実装。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値（0 以下や整数変換失敗）はデフォルトにフォールバックし警告を出力。
  - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB を参照する想定）。
  - 停止フラグ（data/stop_requested.flag）検出でループを終了し、接続を確実にクローズする。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでプロセス優先度を設定する set_process_priority(level) を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
  - CPU affinity を最初 N コアに固定する set_cpu_affinity(cpu_count) を追加。
  - 権限不足・未対応プラットフォームに対しては警告を出して処理をスキップするフォールトトレラント設計。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分（全スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバックし警告。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数決定ロジックを実装。
    - lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap とスケーリングを実装。
    - スケールダウン時の端数配分ロジック（残余キャッシュで fractional remainder が大きい順に lot 単位で追加）を実装。
    - 価格欠損時はスキップしログ出力する等の安全策を追加。

- 研究 / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を使って計算。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮した実装。
    - calc_value: raw_financials から最新の財務データ（target_date 以前）を取得し PER/ROE を算出。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括 SQL で計算。horizons のバリデーションを実装。
    - calc_ic: スピアマンランク相関（IC）を計算。必要に満たない場合は None を返す。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
  - research.__init__ で便利関数をエクスポート（zscore_normalize を含む）。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - ニュース集約と OpenAI API（gpt-4o-mini）でのセンチメントスコアリング設計を実装。
  - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を正確に算出する関数を追加。
  - score_news: API キー解決、ウィンドウ計算、API キー未設定時の例外（ValueError）を実装。設計としてバッチ処理上限、スコアのクリップ、リトライポリシー（指数バックオフ）、レスポンス検証、部分成功時の DB 書き換え戦略（対象コードのみ置換）を想定。
  - 設定可能なパラメータ: バッチサイズ、モデル名、最大記事数・文字数、P95 等。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。
  - CLI オプション --from / --to / --db に対応。
  - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均・最大・P95）を集計し、基準値に対する PASS/FAIL 判定を表示。
  - P95 計算、日時フィルタ生成、DB 存在チェック、例外時のフォールバック（OperationalError を捕捉して値を初期化）を実装。

### Changed（変更）
- 起動スクリプト類（run_monitoring / run_execution）は起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority を共通で使用）。
- .env 読み込みの優先順位を OS 環境 > .env.local > .env と明確化。
- monitoring は環境に依存せず本番 sqlite_path を参照する設計に明記（監視データは本番を基準とする）。

### Fixed（修正）
- MONITOR_POLL_INTERVAL の不正値（0 や負数、整数変換失敗）を検出し、デフォルト値にフォールバックする挙動を実装（time.sleep に渡す前の安全策）。
- DuckDB / SQLite への接続確実クローズを finally ブロックで保証（監視・実行の両スクリプト）。

### Security（セキュリティ）
- .env の自動上書き時に OS 環境変数を保護する仕組みを導入（protected set を使用）。
- OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）で指定することを必須化。未設定の場合は ValueError を送出。

### Known issues / Notes（既知の課題・注意点）
- ai/news_nlp モジュールの記事取得・DB 更新ロジックの一部がスニペットで切れているため、完全動作確認が必要です。
- position_sizing における price が欠損（0.0）の場合、現在はスキップしており、将来的にはフォールバック価格導入を検討すべき旨がコメントで残っています。
- set_process_priority / set_cpu_affinity は psutil 依存であり、権限不足や未対応プラットフォームでは設定がスキップされる旨のログ警告が出ます。

---

過去のリリース履歴が存在しないため、上記を初回リリース（0.1.0）相当として記載しました。必要があれば、各モジュールごとにより細かい変更履歴やリリース日・コミット参照を追記できます。