CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース: KabuSys のコア機能群を実装。
  - 実行 / 監視ランチャー
    - run_execution.py: ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔を上書き可能。
    - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を利用）。
  - 設定管理
    - kabusys.config.Settings: 環境変数/.env 読み込みロジックと多数の設定プロパティを実装（DB パス、API トークン、監視閾値、PID / kill flag パス、env/log_level 判定など）。
    - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。OS 環境変数を保護する仕組みあり。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export プレフィクス、クォート値内のエスケープ、インラインコメントの取り扱いをサポート。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。スコア全ゼロ時は等配分にフォールバックして warning を出力。
    - portfolio.risk_adjustment: セクター集中制限の apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear）。
    - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積。
  - 監視・実行周りのユーティリティ
    - utils.process_priority: Windows / POSIX 間を吸収した set_process_priority と CPU 固定用 set_cpu_affinity を実装。権限不足や未対応環境では警告を出してスキップ。
  - リサーチ / ファクター群（DuckDB ベース）
    - research.factor_research: Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB SQL で計算。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary（基本統計量）。
    - すべて外部 API に依存せず prices_daily / raw_financials テーブルのみ参照する設計。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとに ai_scores テーブルへ書き込む処理を実装。チャンクバッチ処理（最大 20 銘柄/コール）、エクスポネンシャルバックオフでのリトライ（429/5xx/ネットワーク等）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に他コードを保護する書き込み戦略を採用。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプト。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して CLI に出力。しきい値（デフォルト）を定義し PASS/FAIL を判定。

Changed
- 監視の DB 接続方式
  - run_monitoring.py は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する仕様を明示。監視データは本番の監視 DB を対象に集計する想定。
- 実行エンジンの DB 分離
  - run_execution.py は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）を使用して発注データを本番 DB と分離する挙動を実装。
- 環境変数ロード順序
  - 自動ロードの優先順位は OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を上書きしないが、override=True により .env.local は .env の上書きとして扱う）。

Fixed
- MONITOR_POLL_INTERVAL の堅牢化
  - 環境変数 MONITOR_POLL_INTERVAL を整数で受け取り、0 以下や不正値は警告ログを出してデフォルト（60 秒）にフォールバックするよう改善。time.sleep に渡せない値を防止。
- calc_score_weights のゼロスコア対処
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分にフォールバックして warning を出すよう修正。
- position_sizing の aggregate スケーリング
  - 全銘柄合計が available_cash を超える場合のスケールダウン処理を実装。スケール後の端数は lot_size 単位で残差順に再配分することでより一貫した割り当てを実現。
- .env パースの強化
  - export プレフィクス、クォート中のバックスラッシュエスケープ、インラインコメント取り扱いなどに対応し、より現実的な .env ファイルを正しく読み込めるように改善。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を導入する余地がある（コード内に TODO を記載）。
- ai.news_nlp は OpenAI API キーの存在を前提とする。キー未設定時は ValueError を送出する。
- research モジュールは DuckDB の prices_daily / raw_financials スキーマに依存する。テーブル構造・NULL の扱いに注意。

Acknowledgements
- 本リリースはプロジェクトの最初の安定的な機能群を提供します。今後のリリースでドキュメント、テスト、エラーハンドリング、設定の柔軟性（例: 銘柄別 lot_size）、およびパフォーマンス改善を予定しています。