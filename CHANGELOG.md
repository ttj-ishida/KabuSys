CHANGELOG
=========

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
- 実行エントリ / デーモン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite(DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可) を使用し、MockBrokerClient を利用して本番 DB と完全分離して実行可能。
    - プロセス起動直後にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を呼び出し）。
    - ExecutionEngine の起動に必要な依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler 等）の組み立て処理を実装。RiskManager のデフォルト設定値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - DuckDB を分析用途で併用（設定から duckdb_path を取得）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックし、警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH、デフォルト data/monitoring.db）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定、例外が発生してもループを継続してログ出力、KeyboardInterrupt による正常終了対応。
- 設定管理
  - kabusys.config.Settings を導入。
    - .env / .env.local の自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合）。読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーは export 形式・クォート・エスケープ・インラインコメント処理に対応（堅牢なパース）。
    - 各種環境変数の取得プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL, KABUSYS_ENV 等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - KABUSYS_ENV および LOG_LEVEL の許容値チェック。必須キー未設定時は ValueError を送出する _require を実装。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順、タイブレークは signal_rank で選定。
    - calc_equal_weights / calc_score_weights: 等金額/スコア重みを計算。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限判定（既存保有のセクター時価を計算し上限を超えるセクターの候補を除外）。sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能。unknown セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数を返す。未知レジームは警告ログの上で 1.0 にフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づいて発注株数を算出。lot_size（単元）で丸め、per-stock 上限・aggregate cap（available_cash） を考慮。cost_buffer を使った保守的コスト見積もりと、資金超過時のスケーリング（端数は lot 単位で残差順に追加配分）を実装。
- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定。未対応 OS や権限不足時は警告を出力して安全にスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を設定（引数検証・権限不足ハンドリングあり）。
- 研究（Research）機能
  - kabusys.research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いて各種ファクター（モメンタム、ATR、平均出来高、PER/ROE 等）を計算する SQL 実装を追加。窓幅不足時は None を返す設計。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得する効率的クエリ。
    - calc_ic / rank / factor_summary: スピアマン IC（ランク相関）計算、ランク関数（同順位平均ランク）、ファクター統計サマリを実装。小データ/欠損値に対する安全化（None 返却）あり。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI / ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news を OpenAI API (gpt-4o-mini) に送りセンチメントスコアを算出し、ai_scores テーブルへ書き込むロジックを追加。
    - 処理の流れ: 対象ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30）、記事集約（銘柄ごとに記事数・文字数制限）、最大 20 銘柄単位でのバッチ送信、429/5xx/タイムアウト等に対する再試行（指数バックオフ）、レスポンス検証、スコアのクリップ（±1.0）、部分失敗が起きても他銘柄を保護する形で DB 書換を行う（DELETE → INSERT）。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - calc_news_window 関数でウィンドウ計算を提供（UTC naive datetime を返却）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。コマンドライン引数 --from / --to / --db をサポート。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、閾値に基づく PASS/FAIL レポートを標準出力に出力。DB が存在しない、テーブルがない場合は適切に N/A 等で扱う。P95 は独自実装で空リストは None を返す。
- パッケージ情報
  - __version__ = "0.1.0" を設定。
  - kabusys パッケージの主要エクスポート（portfolio, research など）を __all__ 経由で整備。

Changed
- （新規リリースにつき該当なし）

Fixed
- .env パース:
  - クォート内のバックスラッシュエスケープ、インラインコメント、export プレフィックス等に対応し、より堅牢な .env 読み込みを実現。
- その他多くの関数で欠損データ・ゼロ除算・権限不足・未対応プラットフォームなどを想定したガードを追加し、安全にスキップしてログを出す挙動を採用。

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数から解決し、未設定時はエラーを出す（誤設定による API 事故を防止）。

Notes / Known issues / TODO
- position_sizing の price が欠損（0.0）の場合、現状では exposure が過少見積りされセクター上限判定が甘くなる可能性がある（portfolio.risk_adjustment.apply_sector_cap 内に TODO コメントあり）。将来的に前日終値や取得原価でのフォールバック処理を推奨。
- ai.news_nlp 内の一部ヘルパー（記事取得・チャンク処理の詳細実装）はここに含まれるファイルで部分的に省略されているため、実運用前にエンドツーエンドでの検証を推奨。
- DuckDB/SQLite への書き込みや executemany の挙動は環境に依存するため、本番運用前に DB バックアップとスキーマ検証を行ってください。

以上。検出された不具合や追加要望は issue/ticket にて管理してください。