CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-12
-----------------

Added
- 初回リリース: KabuSys の基本コンポーネント群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - モニタリングは KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を利用）。
      - DB 初期化（init_monitoring_db）、DuckDB 接続を行いループ内で monitor.check_once() を定期実行。
    - run_execution.py
      - ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine.run_session() を実行。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.py
      - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env のパース処理を詳細実装（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
      - 環境変数取得のヘルパー _require() と Settings クラスを提供。多くのプロパティを定義（J-Quants / kabu / LINE / DB パス / 監視・閾値 / システム設定等）。
      - PAPER_FILL_MODE の値チェック（instant, partial, never, reject）とエラーハンドリング。
      - デフォルト値を明示（例: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db）。
  - モニタリング
    - monitoring.monitoring_db.init_monitoring_db（DB 初期化を保証、冪等）。
  - ユーティリティ
    - utils/process_priority.py
      - Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティを追加。
      - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
      - サポート外 OS や権限不足時はログで警告しスキップする安全設計。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等重み calc_equal_weights、スコア加重 calc_score_weights（スコア合計が 0 の場合に等金額配分へフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap（既存保有のセクター暴露に基づく候補除外）、calc_regime_multiplier（レジームに応じた投下資金乗数。未知レジームは警告のうえ 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes による株数決定ロジック。
      - allocation_method="risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリングと残差処理を実装（残差の大きい順に lot 単位で追加配分）。
  - リサーチ（DuckDB ベース）
    - research/factor_research.py
      - calc_momentum / calc_volatility / calc_value を提供。prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、出来高、PER/ROE 等）を計算。
      - データ不足時は None を返すなど堅牢な実装。
    - research/feature_exploration.py
      - calc_forward_returns（将来リターン）、calc_ic（Spearman のランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
      - rank() は丸めにより浮動小数点の ties 検出漏れを防止。
    - research/__init__.py で主要 API をエクスポート（zscore_normalize は kabusys.data.stats から）。
  - AI: ニュース NLP スコアリング
    - ai/news_nlp.py
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、各銘柄のセンチメントを -1.0〜1.0 に正規化して ai_scores に書き込む機能を実装。
      - チャンクサイズ 20、1銘柄あたり最大記事数・最大文字数トリムを実装。JSON Mode のレスポンス検証、スコアクリッピング、エラー（429/ネットワーク/5xx）に対する指数バックオフリトライを実装。
      - OpenAI API キー未設定時は ValueError を送出。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
      - システム稼働率・注文成功率・送信率・レイテンシ（P95）等を集約して PASS/FAIL 判定を出力する。デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。
      - DB テーブル存在チェック・例外（OperationalError）ハンドリングにより堅牢化。
  - パッケージエクスポート
    - portfolio / research の主要関数をモジュール top-level にエクスポートする __all__ を整備。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の留意点
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊な配置では自動ロードがスキップされることがあるため、必要に応じて環境変数を明示的に設定してください。
- run_monitoring は監視用 DB に常に sqlite_path（production 相当）を使う設計です。テスト用に監視も分離したい場合は DB パスやスクリプトを変更してください。
- ai/news_nlp は OpenAI を利用するため、API キーの設定とコスト・レート制限に注意してください。部分的にスコア取得に失敗した場合でも既存のスコア保護のために更新範囲を限定する等の安全策を取っています。
- position_sizing の株数丸めや aggregate スケーリングは lot_size 固定（現状 100）前提。将来的に銘柄別単位のサポートを想定する TODO が残っています。
- calc_forward_returns の horizons は 1〜252 の範囲で検査を行い、無効な値は ValueError を送出します。
- process_priority 系は権限不足やプラットフォーム非対応時に例外を投げず警告ログでスキップする設計です。

Security
- （初回リリースのため該当なし）

貢献・問い合わせ
- バグ報告や機能要望はリポジトリの Issue に投稿してください。