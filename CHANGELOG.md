CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （現時点の未リリース変更はありません）

0.1.0 - 2026-04-12
-----------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: kabusys.__version__ = 0.1.0
- 実行用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - プロセス優先度を設定（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成・OrderManager / RiskManager / Reconciler 組立て・engine.run_session() を実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視は本番 DB を参照する仕様）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理（.env 自動読み込み・検証）を追加。
  - config.Settings
    - .env / .env.local の自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 強力な .env パーサ（export 形式、クォート内エスケープ、インラインコメント処理等）。
    - 必須環境変数取得ヘルパ（_require）と多くのプロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_*、閾値等）。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の入力検証（不正値時は ValueError）。
- ポートフォリオ構築関連の純関数群を追加（DB参照なし）。
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + tie-breaker で候補選定
    - calc_equal_weights, calc_score_weights（スコアゼロ時は等配分へフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") をサポート。lot_size、cost_buffer、max_position_pct、max_utilization、aggregate cap スケーリング、端数処理（lot 単位での配分）を実装。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジション考慮・売却予定コード除外対応）
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数（未知レジームは警告を出して 1.0 フォールバック）
- 監視・検証ツールを追加。
  - tools.paper_verification_report
    - Paper Trading 用 SQLite を解析し検証レポートを標準出力に生成（期間指定可）。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定。
    - DB が存在しない場合やテーブル不備に対する安全ハンドリングあり。
- 研究（research）モジュールを追加。
  - research.factor_research: calc_momentum, calc_volatility, calc_value（DuckDB 経由で prices_daily / raw_financials を参照）
  - research.feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank
  - research パブリック API を __all__ で公開（zscore_normalize を data.stats から取り込み）
- AI ニュース NLP スコアリングを追加（部分実装）。
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信、銘柄ごとのセンチメントスコアを ai_scores に書き込む設計。
    - バッチサイズ、記事/文字数制限、ウィンドウ計算（JST→UTC 変換）、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンス検証、±1.0 でのクリップ等を考慮。
- ユーティリティを追加。
  - utils.process_priority: set_process_priority(level)（Windows / POSIX の差分吸収）、set_cpu_affinity(cpu_count)（最初の N コアにピン留め）。権限不足等は警告でスキップ。

Changed
- 監視系の挙動設計
  - run_monitoring は環境（KABUSYS_ENV）に依存せず常に production sqlite_path を使用する方針を明示。
- .env の自動読み込みロジック
  - OS 環境変数を保護する protected 機構を導入（.env.local は override=True、ただし既存 OS 環境変数は上書きしない）。
- 設計方針の明示
  - 研究／ファクター計算は DuckDB の prices_daily / raw_financials だけを参照し、本番 API にアクセスしない方針を明記。
  - AI スコアリングはルックアヘッドバイアスを防ぐために datetime.today()/date.today() を直接参照しない設計。

Fixed / Hardened
- .env パーサを堅牢化
  - export 形式やクォート内のバックスラッシュエスケープ、インラインコメントの扱いを実装し、不正行を無視するように。
- 各種関数での欠損データ・DB不在時の安全処理を追加
  - paper_verification_report: テーブル欠如や DB ファイル無しでもエラーメッセージを出力して安全に終了。
  - factor / volatility / forward returns の計算はウィンドウ不足時に None を返す等、欠損に対する明確な振る舞いを採用。
- process_priority / cpu_affinity は権限不足や未対応プラットフォーム時に例外を投げず警告でスキップするように調整。

Environment / Configuration (主な環境変数)
- KABUSYS_ENV (development | paper_trading | live)
- KABUSYS_DISABLE_AUTO_ENV_LOAD
- MONITOR_POLL_INTERVAL
- PAPER_FILL_MODE (instant | partial | never | reject)
- PAPER_TRADING_SQLITE_PATH
- SQLITE_PATH, DUCKDB_PATH
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- LOG_LEVEL

Notes
- 本リリースは初期実装であり、API の具体的なブローカークライアント実装や SystemMonitor の内部実装、ai.news_nlp の完全な永続化処理（ファイル切替やトランザクションの細部）などは今後の改良対象です。
- 実行時の権限やプラットフォーム差分（プロセス優先度設定等）により一部機能は警告を出してスキップされる場合があります。運用環境に応じた権限設定を推奨します。