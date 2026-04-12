Keep a Changelog
=================

すべての公開変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

0.1.0 - 2026-04-12
------------------

Added
- 初回リリース。
- 実行用エントリポイントを追加:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - プロセス優先度を最初に "high" に設定する処理を実行。  
    - KABUYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用することで本番 DB と完全分離。  
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション起動処理を提供。  
    - RiskConfig による標準的なリスク制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。  
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db）。  
    - duckdb 接続も同時に確立し、監視ループ内で monitor.check_once() を呼び出す実装。
- 設定管理モジュールを追加:
  - config.py: プロジェクトルートから .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env の堅牢なパース実装を提供（export 文、クォート、エスケープ、インラインコメント等に対応）。  
  - Settings クラスで多数の環境変数に対するプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視・閾値設定 / 環境判定等）。値の検証（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）を実施。
- ポートフォリオ構築ユーティリティを追加（純粋関数群、DB参照なし）:
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全ゼロ時は等配分にフォールバックして警告を出力。
  - portfolio.position_sizing: allocation_method ("risk_based", "equal", "score") に基づく買付株数計算を実装。単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケールダウンと端数再配分ロジックを備える。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を提供。未知レジームはフォールバックし警告を出力。
- 研究（Research）モジュールを追加:
  - research.factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクター計算（DuckDB を用いた SQL ベース実装）。各ファクターは欠損やデータ不足を考慮して None を返す設計。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。外部依存を避け標準ライブラリのみで計算。
  - research パッケージの __init__ で主要関数を公開（zscore_normalize を含む）。
- AI ニュース NLP モジュールを追加:
  - ai.news_nlp: raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI API（gpt-4o-mini + JSON Mode）へバッチ送信してセンチメントスコアを ai_scores テーブルへ記録する機能を実装。  
    - バッチサイズ、トークン膨張対策（記事数・文字数トリム）、タイムウィンドウ計算（JST基準の前日15:00〜当日08:30 を UTC に変換）を含む。  
    - 429/ネットワーク/5xx に対して指数バックオフでリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗に備えた部分置換（対象 code のみ DELETE→INSERT）等の堅牢な設計。
- 分析・検証ツールを追加:
  - tools.paper_verification_report: Paper Trading 用 SQLite を解析して稼働率・注文成功率・送信率・レイテンシ等の指標を出力する CLI ツールを提供。閾値（稼働率99%、成功率90%、送信率95%、P95レイテンシ200ms）による PASS/FAIL 判定を実装。期間フィルタ（--from/--to）や DB パス指定（--db）に対応。
- ユーティリティを追加:
  - utils.process_priority: Windows/Linux/Mac の差分を吸収してプロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）を設定するユーティリティを実装。権限不足や未対応プラットフォームでは警告を出して処理をスキップする堅牢な実装。
- パッケージ情報:
  - __init__.py にて __version__ = "0.1.0" を設定。公開 API を __all__ で整理。

Changed
- なし（初回リリースのため変更履歴は追加項目のみ）。

Fixed
- 設定/入力の堅牢化:
  - MONITOR_POLL_INTERVAL の不正な値（0 以下や非整数）を検出して警告しデフォルトにフォールバックする実装を追加。これにより time.sleep に渡す不正値による例外を回避。
  - .env パーサーでのクォート処理、エスケープ、インラインコメント処理、export プレフィックス対応により .env の解釈を堅牢化。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値チェックを行い、不正な値は ValueError を送出して早期発見可能に。
- DB/IO の堅牢化:
  - tools.paper_verification_report と各モジュールで SQLite / DuckDB 接続時の OperationalError をキャッチしてデフォルト値で処理を継続するフェイルセーフを導入。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーの取り扱い: ai.news_nlp.score_news は API キーが引数/環境変数で未設定の場合に ValueError を送出し、未設定での実行を防止します。

注記
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行います。配布後にプロジェクトルートが特定できない場合は自動ロードをスキップします。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 動作は本番システムと DB を物理的に分離する設計になっています（paper_trading 専用 DB を使用）。
- 一部の TODO（例: position_sizing の銘柄別 lot_size のサポート、apply_sector_cap の価格欠損時のフォールバック等）がソース内コメントとして残っています。

今後の予定（短期）
- 単元毎の lot_size を銘柄別に扱えるよう position_sizing の拡張。
- apply_sector_cap の価格欠損に対する前日終値などのフォールバック実装。
- ai.news_nlp の部分失敗時のリカバリ手順強化（永続化戦略の改善）。