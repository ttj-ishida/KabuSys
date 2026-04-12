CHANGELOG
=========

このファイルは Keep a Changelog の規約に準拠して記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のコードベースでは未リリースの変更はありません）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース: KabuSys コードベースを公開。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper-trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を利用し、MockBrokerClient 経由で完全に本番 DB と分離して動作する設計。
    - ブローカークライアントの生成は BrokerClientFactory 経由。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig や EngineConfig を用いた初期設定（例: max_position_pct, rate_limit_per_sec, initial_portfolio_value = broker.get_available_cash() 等）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視データは本番側に記録）。
    - プロセス優先度を起動時に "high" に設定するフローを搭載（set_process_priority を呼び出し）。
- 設定管理:
  - config.py: Settings クラスを導入し、環境変数／.env ファイルから各種設定を取得する仕組みを提供。  
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env → .env.local を読み込み。OS 環境変数は保護される（上書きされない）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ: export 形式、シングル／ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings に多数のプロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/KILL フラグパス / ログレベル / env 判定 等）。PAPER_FILL_MODE の値検証や KABUSYS_ENV の検証を含む。
- ポートフォリオ構築（純粋関数群、メモリ内計算のみ）:
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights。
    - score が全て 0 の場合は calc_score_weights が等金額配分へフォールバックし WARNING をログ出力。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限を適用）、calc_regime_multiplier（market regime に応じた乗数）。
  - portfolio.position_sizing: calc_position_sizes（allocation_method="risk_based" / "equal" / "score" 対応）。  
    - 単元株（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリング、スケーリング後の残差配分ロジックを実装。
- 研究・ファクター計算:
  - research.factor_research: calc_momentum, calc_volatility, calc_value（DuckDB 上の prices_daily / raw_financials を利用）。200日移動平均やATR等の計算を SQL ウィンドウ関数で実装。
  - research.feature_exploration: calc_forward_returns（任意ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）、rank（平均ランク tie 処理）。外部ライブラリに依存しない実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。
- AI ニュース NLP:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）に送ってセンチメント（-1.0〜1.0）を計算し、ai_scores テーブルへ書き込む機能を追加。  
    - バッチ処理（最大 20 銘柄 / コール）、記事数・文字数トリム、429/5xx/ネットワーク障害に対する指数バックオフリトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 でのクリップを実装。
    - ルックアヘッドバイアスを避けるため、内部で日付や現在時刻を直接参照しない設計（target_date を明示的に受け取る）。
- ツール:
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、PASS/FAIL を判定（デフォルト閾値をコードコメントで指定）。P95 は内部実装でソート・索引指定により算出。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH からの参照も可能。
- ユーティリティ:
  - utils.process_priority: set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows / POSIX の差分吸収、アクセス権限不足や未対応プラットフォーム時は警告でフォールバック。

Changed
- ロギング・起動フロー:
  - run_execution.py / run_monitoring.py は起動時に logging.basicConfig(level=logging.INFO) を実行し、初動でプロセス優先度を設定するようにした（set_process_priority("high")）。
- DB 接続ポリシー:
  - run_monitoring は監視テーブル用に Settings.sqlite_path（本番）を常に使用する仕様（環境に依存しない）。run_execution は paper_trading 環境時に専用紙トレ DB を使う。

Fixed
- 環境変数パースの堅牢化:
  - _parse_env_line により export プレフィックス、クォート内エスケープ、インラインコメントの扱いを改善。無効行は無害にスキップ。
- MONITOR_POLL_INTERVAL の無効値ハンドリング:
  - run_monitoring._get_poll_interval が 0 以下や非整数を検出した場合にデフォルト（60 秒）へフォールバックし、warning を出力するようにした（time.sleep に渡す不正値回避）。
- DuckDB / SQLite クエリの安全策:
  - tools.paper_verification_report の各クエリ周りで sqlite3.OperationalError を捕捉してデフォルト値にフォールバックし、DB スキーマ不在時にもツールが壊れないようにした。

Security
- OpenAI API キーの取り扱い:
  - ai.news_nlp.score_news は明示的な api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出して明示的に失敗させる（キー無しで不正に API を叩かない）。

Notes / Known limitations
- apply_sector_cap: price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性があり、将来的に前日終値等のフォールバックを導入予定（TODO コメントあり）。
- calc_position_sizes:
  - lot_size は現状グローバル共通の単元数を仮定。将来的に銘柄別単元マップへの拡張を想定。
  - aggregate スケーリング時は lot_size 単位での再配分を行うが、稀に小数点や残余で最適解が得られないケースがある。
- news_nlp:
  - API のレスポンス仕様（JSON Mode で results キーが存在すること）に依存。外部 API の変化があると処理失敗のリスクがある。
- research モジュール群と portfolio モジュール群は DuckDB / prices_daily / raw_financials 等の前提データが揃っていることを要する（実行環境のデータ準備が必要）。

Authors
- KabuSys 開発チーム（コード内コメント・モジュール設計に基づく初回リリース）

License
- プロジェクトのライセンスはリポジトリのルートに従ってください（pyproject.toml / LICENSE 等）。