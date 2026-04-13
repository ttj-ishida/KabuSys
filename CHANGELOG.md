Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
タグは SemVer に従います。

0.1.0 - 2026-04-13
-----------------

Added
- パッケージ初期リリース（kabusys 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - プロセス優先度を "high" に設定して実行。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（MockBrokerClient による paper_trading モード対応）。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立てて engine.run_session() を呼び出す。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - OS 環境変数優先、.env.local は上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env パーサーは export 形式・クォート・エスケープ・インラインコメントに対応。
    - Settings クラスを提供し、さまざまな環境変数をプロパティとして取得可能に：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
      - PAPER_FILL_MODE（instant|partial|never|reject。無効値は ValueError）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU/MEM/DISK の閾値（CPU_THRESHOLD_PCT 等）
      - KABUSYS_ENV の検証（development, paper_trading, live）
- モジュール群：ポートフォリオ構築
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: スコア降順＋タイブレークで signal_rank を考慮して候補を選定。
      - calc_equal_weights / calc_score_weights（スコア全0 の場合に等金額配分へフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有のセクターエクスポージャーが指定比率を超える場合に新規候補を除外（"unknown" セクターは除外しない）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3。未知値は警告の上 1.0 にフォールバック）。
    - position_sizing.py
      - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap のスケールダウン、cost_buffer による保守的見積り、残差分の lot 単位での再配分ロジックを実装。
- 監視・ユーティリティ
  - utils.process_priority.py
    - set_process_priority(level) により Windows / POSIX を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定するユーティリティを追加。
    - 権限不足や未対応プラットフォーム時には警告を出して安全にスキップ。
- 研究・データ処理
  - research.factor_research.py
    - モメンタム / ボラティリティ / バリューのファクター計算関数（calc_momentum, calc_volatility, calc_value）を DuckDB 接続を受けて実装。200 日移動平均、ATR、20 日平均出来高、PER/ROE 等を算出。
  - research.feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、rank / factor_summary 等の統計ユーティリティを実装。外部依存（pandas 等）なしで標準ライブラリのみで実装。
  - research.__init__.py で主要関数をエクスポート。
- AI ニュース NLP
  - ai.news_nlp.py
    - raw_news -> OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコア生成機能を追加。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウで記事を集約、1 銘柄あたり記事数/文字数制限を実施（最大 10 記事、3000 文字）。
    - 最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンス検証、スコアを ±1.0 にクリップ、ai_scores テーブルへ部分置換（スコア取得できた銘柄のみ置換）を行うフェイルセーフな設計。
- ツール
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト（CLI）。
    - フィルタ期間指定 (--from / --to)、DB パス指定 (--db) をサポート。PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能。
    - システム稼働率・注文成功率・送信率・P95 レイテンシなどを集計し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200 ms）に基づく PASS/FAIL を判定して標準出力に整形レポートを出力。

Changed
- パッケージエクスポート（kabusys.__init__）で初期バージョンを設定（__version__ = "0.1.0"）し、主要サブパッケージを __all__ に追加。

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キー等の機密情報は環境変数で取得する設計。自動 .env ロードでは既存 OS 環境変数を保護するため上書きを制御。

Notes / 今後の改良ポイント
- position_sizing.calc_position_sizes: price が 0.0 の場合のエクスポージャー過少見積りや、将来的な lot_size 銘柄別対応（現状は共通 lot_size）に関する TODO が記載されています。
- ai.news_nlp の API 呼び出し周りは詳細なエラーハンドリング・ログ・メトリクス等でさらに強化可能。
- duckdb / sqlite のスキーマや SystemMonitor / ExecutionEngine の詳細実装（このリリースではエントリポイントと連携ロジックを提供）については今後のドキュメント整備を予定。

--- 
この CHANGELOG はソースコードから推測して作成されています。詳細な仕様・変更履歴は実際のコミット履歴や設計ドキュメントを参照してください。