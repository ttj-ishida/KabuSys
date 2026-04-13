CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットで管理されています。  
このファイルは日本語で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（現時点のスナップショットはリリース 0.1.0 として初回公開済みです。以降の変更はここに記載します。）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
  - 実行・監視バイナリ/スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し MockBrokerClient を利用することで本番 DB と完全分離する設計。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼出し）。
      - DuckDB 接続 (DUCKDB_PATH, デフォルト: data/kabusys.duckdb) を受け取り、ExecutionEngine を構築してセッションを実行。
      - Execution に必要なコンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を組み立てる。
      - RiskConfig のデフォルト値（max_position_pct、max_utilization、rate_limit_per_sec など）を設定。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60秒）。不正値（0以下や非整数）はデフォルトにフォールバックして警告出力する。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する点に注意。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定・環境管理
    - config.Settings
      - .env/.env.local を自動ロードする仕組み（プロジェクトルートを .git または pyproject.toml で検出）。
      - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env ファイルのパースは export 形式、クォート、エスケープ、インラインコメント等に対応。
      - 環境変数の必須チェック関数 _require を提供（未設定時は ValueError）。
      - 各種設定プロパティを提供:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
        - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
        - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
        - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト data/monitoring.db）
        - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
        - PAPER_FILL_MODE（instant/partial/never/reject の検証あり、デフォルト instant）
        - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
        - CPU/MEM/DISK しきい値（CPU_THRESHOLD_PCT 等）
        - KABUSYS_ENV の検証（development / paper_trading / live）
        - LOG_LEVEL の検証
      - settings = Settings() をモジュールレベルでエクスポート
  - プロセス制御ユーティリティ
    - utils.process_priority.set_process_priority(level)
      - Windows と POSIX（Linux/Mac/FreeBSD）間の差分を吸収して優先度を設定。
      - アクセス権限不足等の場合は警告を出して失敗をスキップする安全策を実装。
    - utils.process_priority.set_cpu_affinity(cpu_count)
      - 指定コア数にプロセスをピン留めするユーティリティ（None の場合は何もしない）。エラー時は警告出力でフォールバック。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順、同点時は signal_rank でタイブレークして上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（全スコアが 0 の場合は等分へフォールバックして警告）。
    - portfolio.risk_adjustment
      - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外しない）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート）。未知レジームは警告を出して 1.0 でフォールバック。
    - portfolio.position_sizing
      - calc_position_sizes:
        - allocation_method: "risk_based" / "equal" / "score" をサポート。
        - lot_size（単元）丸め、max_position_pct・max_utilization に基づく上限、cost_buffer を考慮した保守的見積り。
        - aggregate cap 超過時のスケーリングと端数処理（lot 単位での再配分）を実装。
  - リサーチ・ファクター計算
    - research.factor_research
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。データ不足時の None 礼遇。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。NULL の伝播を考慮した実装。
      - calc_value: raw_financials から直近の財務データを取得し PER / ROE を算出。
      - DuckDB を用いた SQL ベースの高速実行を想定。
    - research.feature_exploration
      - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（horizons 検証あり）。
      - calc_ic: スピアマンランク相関（IC）を計算。3 銘柄未満で計算不能なら None を返す。
      - factor_summary / rank: 基本統計量・ランク変換の純粋関数を提供。
  - AI ニュース NLP（OpenAI 統合）
    - ai.news_nlp
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書込むワークフローを実装。
      - calc_news_window(target_date): 日本時間の前日 15:00 ～ 当日 08:30（UTC に変換）を扱うウィンドウ計算ユーティリティ。
      - score_news(conn, target_date, api_key=None): API キーの解決・記事集約・バッチ送信・リトライ（429/ネットワーク/5xx に指数バックオフ）・レスポンス検証・スコアクリップ・部分成功時の DB 保全（更新対象コードに限定して DELETE/INSERT）などの設計方針を実装。
      - バッチサイズや最大トークン対策等の定数はモジュール内で明示（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK 等）。
  - ユーティリティ・ツール
    - tools.paper_verification_report
      - Paper Trading 用検証レポート生成 CLI。
      - コマンド例: python -m kabusys.tools.paper_verification_report
      - 日付フィルタ --from / --to、DB パス指定 --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等を計算し PASS/FAIL 判定を出力。
      - P95 計算、各種 NULL ハンドリング、テーブル未存在時の安全なフォールバックを実装。
  - パッケージメタ情報
    - パッケージバージョン: __version__ = "0.1.0"
    - エクスポート: research, portfolio 等の __all__ を整備。

Changed
- 初回リリースのため履歴なし（すべて Added）。

Fixed
- 初回リリースのため履歴なし。

Security
- 初回リリースのため履歴なし。

Notes / 実装上の重要な挙動
- .env の自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や CWD が異なる状況でも期待通り動作するよう設計されています。ルートが見つからない場合は自動ロードをスキップします。
- run_monitoring は監視データを書込む SQLite DB として Settings.sqlite_path を常に使用します（環境に関わらず本番向け path を参照する設計）。Paper trading と監視 DB は分離される点に注意してください。
- process priority / CPU affinity の設定は実行環境の権限に依存します。権限不足時は警告を出して処理を継続します。
- OpenAI API 統合は API キーの設定（引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は ValueError を送出します。
- Paper Trading 検証レポートの閾値（稼働率・成功率等）はモジュール内定数で管理されており、将来的に引数化・外部化する余地があります。

今後の予定（例）
- unit tests の追加（各 pure function / SQL クエリのテスト）
- ドキュメント整備（PortfolioConstruction.md / StrategyModel.md 参照先の公開）
- ai.news_nlp の堅牢化（API レスポンススキーマ検証の強化、レートリミット監視）
- ExecutionEngine と Monitoring の監視・メトリクス強化（Prometheus 等）

お問い合わせ
- バグ報告・機能要望はリポジトリの Issue へお願いします。