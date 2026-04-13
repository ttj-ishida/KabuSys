CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

バージョン
---------

Unreleased
----------
（現時点のリリースノートはありません）

0.1.0 — 2026-04-13
------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行用エントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境変数 KABUSYS_ENV が "paper_trading" の場合は paper_trading 用の専用 SQLite DB (デフォルト: data/paper_trading.db) を使用し、本番 DB と完全分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを実装。
    - duckdb を分析向けに併用（settings.duckdb_path）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値・0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理モジュールを実装。
  - config.Settings: 環境変数をラップして取得するプロパティ群を提供（DB パス、PID/KILL フラグ、閾値、API トークンなど）。
  - 自動 .env ロード実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - 読み込み順序: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式やクォート、インラインコメントなどに対応。
  - 各種環境変数の妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- モニタリング DB 初期化ユーティリティを導入（monitoring.monitoring_db.init_monitoring_db を使用）。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補抽出（signal_rank で同点ブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック、警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別の既存エクスポージャーを基に新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数 ("bull"/"neutral"/"bear")。未知レジームは警告して 1.0 フォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算、lot_size（単元）で丸め、per-stock 上限・aggregate cap スケーリング、cost_buffer による保守的見積り、残余キャッシュでの端数配分ロジックを実装。
- 研究・ファクター計算モジュールを追加（kabusys.research）。
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を用いたファクター計算を提供（MA200, ATR20, momentum リターン, PER/ROE 等）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン計算（可変ホライズン、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算。3 レコード未満は None を返す。
    - factor_summary / rank: 統計要約とランク化ユーティリティ。
  - research パッケージは zscore_normalize を data.stats からエクスポートして統合。
- AI ニューススコアリングモジュールを追加（kabusys.ai.news_nlp）。
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコアを計算して ai_scores テーブルに書き込む処理を実装。
  - バッチ処理（_BATCH_SIZE=20）、最大記事数/文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、結果バリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 保護（該当コードだけ置換）等のフェイルセーフ実装。
  - ニュース取得ウィンドウ計算（JST ベース -> UTC 変換）を calc_news_window で提供。
- tools スクリプトを追加。
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツール（コマンドライン引数 --from/--to/--db をサポート）。
    - 検証用基準値を定義（稼働率、注文成功率、送信率、P95 レイテンシ等）と P95 計算、各テーブル（system_status / trade_logs / risk_logs）からの指標抽出、PASS/FAIL 判定とレポート出力。
    - DB が存在しない場合や該当テーブルがない場合のハンドリング（OperationalError をキャッチして N/A を出力）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的にエラーを投げることで不正な運用を防止。

Notes / Implementation details
- DuckDB は分析用途向けに使用（settings.duckdb_path、各 research / ai モジュールで使用）。
- sqlite3 は各種ログ / 監視 / paper_trading 用の永続化に使用。
- プロセス優先度・CPU affinity は kabusys.utils.process_priority に抽象化されており、Windows / POSIX の差異を吸収。設定失敗時はワーニングでスキップするフェイルセーフを持つ。
- 設定の自動読み込みはプロジェクトルートの探索に基づくため、配布後も cwd に依存しない動作を目指す。
- 多くの純粋関数（ポートフォリオ関連、研究関連）は DB を直接変更せずメモリ内計算のみで設計されている（テスタビリティ向上）。

Acknowledgements
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートが存在する場合は、それに従って差し替えてください。