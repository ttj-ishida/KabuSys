# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルでは、リポジトリに含まれるコードから推測した初期リリースの差分・主要機能・既知の注意点を記載しています。

フォーマット:
- 変更はセマンティックバージョニングに基づくカテゴリ別に記載しています。
- 日付はリリース作成日（このドキュメント作成時点）です。

© 2026 KabuSys プロジェクト

Unreleased
----------

（現在未リリースの変更はここに記載されます）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能（OS 環境変数を保護）。
  - 複雑な .env 行のパース（export プレフィックス、クォート、インラインコメント等に対応）。
  - 環境変数の必須チェックユーティリティ（_require）および Settings クラスを提供。
  - 各種設定プロパティ（DB パス、PID/kill フラグのパス、閾値、環境名検証、paper_trading 用設定等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB（data/paper_trading.db をデフォルト）で分離実行。
    - BrokerClientFactory 経由で実ブローカー／モックを選択。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立ておよび起動ロジック。
    - 停止フラグ（data/stop_requested.flag）検出時の安全な停止処理。
    - 実行用 PID ファイル管理（data/execution.pid）。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）が明示的に設定。
- 監視系スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB に記録）。
    - 停止フラグ検出による終了処理、KeyboardInterrupt による終了を適切にハンドリング。
- 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）を両スクリプトで保証（冪等にテーブルを用意）。
- ユーティリティ
  - process_priority（kabusys.utils.process_priority）
    - Windows / POSIX 間の差分を吸収してプロセス優先度（"high"/"normal"/"low"）を設定。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を提供。
    - psutil の例外（AccessDenied 等）を安全に扱い、失敗時は警告して続行。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順 + tie-breaker（signal_rank）で候補選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクターエクスポージャー計算、売却予定銘柄除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、per-position と aggregate の上限（max_position_pct / max_utilization）適用、コストバッファ考慮のスケールダウンロジックを実装。
    - aggregate スケーリング時の残差処理（lot 単位での端数配分）を考慮。
    - price 欠損時のスキップやログ出力に対応。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算実装（windows、スキャン範囲のバッファ、必要データ不足時の None 返却等）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で生成（horizons の検証あり）。
    - calc_ic / rank / factor_summary: Spearman に基づく IC 計算（ランク処理は同順位の平均ランク）、統計サマリー計算。
  - DuckDB 接続を受け取り、外部 API や pandas に依存しない実装方針を採用。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を算出し、定められた閾値で PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。期間フィルタ（--from / --to）対応。
    - レポートの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）をハードコードで定義。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとに ai_scores テーブルへ反映するためのスコアリング処理を実装。
  - 機能: タイムウィンドウ算出（JST→UTC 変換）、銘柄ごとの記事集約（文字数・記事数トリム）、最大 20 銘柄バッチ、JSON 出力検証、スコアクリップ（±1.0）、429/ネットワーク/5xx に対する指数バックオフリトライ。
  - API キー解決（引数 / 環境変数 OPENAI_API_KEY）、未設定時は ValueError。
  - フェイルセーフ設計（API 失敗時は他処理に影響を与えず継続）。
  - （注）ソースの最後が途中で切れているように見えるが、主要設計と多くの実装は含まれる。
- データベース
  - SQLite（監視用/ペーパートレーディング用）と DuckDB（時系列・バッチ集計用）の併用を前提に設計。
  - init_monitoring_db による監視テーブルの冪等初期化を両スクリプトで呼び出し。
- ロギング
  - 各スクリプトは logging.basicConfig(level=logging.INFO) を使用し、重要なイベントは INFO/DEBUG/ WARNING/EXCEPTION で出力。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- （初期リリースのため修正履歴はなし）

Known issues / Notes
- ai/news_nlp モジュールのソースが途中で切れている箇所があり、そこは実装未完了または切断により処理が途中で終了している可能性がある（このドキュメントはコードから推測して作成）。
- position_sizing 内の価格欠損時（price が 0.0）の挙動については TODO コメントあり：前日終値や取得原価などのフォールバック戦略は未実装。
- apply_sector_cap は "unknown" セクターを除外対象にしない設計（意図的）。運用上の注意点を README 等に明記推奨。
- process_priority / set_cpu_affinity は psutil に依存しており、権限不足や未サポートプラットフォームでは警告を出してスキップする仕様。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」とのコメントがあり、開発 / ペーパー環境での誤操作リスクがあるため運用時の注意が必要。
- paper_verification_report は DuckDB ではなく SQLite の paper_trading DB を参照するため、paper_trading 実行結果の記録形式が変わるとレポートが正しく動作しない可能性がある。

References / 運用メモ
- 環境変数の自動読込を無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ポーリング間隔の上書き: MONITOR_POLL_INTERVAL（秒、1 以上の整数。無効値は 60 秒にフォールバック）
- Paper Trading 用 DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- OpenAI API を使う機能: 環境変数 OPENAI_API_KEY をセット
- PID / stop フラグ:
  - 停止フラグ: data/stop_requested.flag
  - 実行 PID: data/execution.pid（run_execution で使用）

この CHANGELOG はコードベースを解析して推測したものであり、実際のリリースノートはリポジトリのコミットログやリリース手順に基づいて補完してください。