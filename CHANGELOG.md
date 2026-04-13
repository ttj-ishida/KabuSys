CHANGELOG
=========

すべての注目すべき変更点をここに記載します。  
フォーマットは Keep a Changelog に準拠します。

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース: KabuSys コードベースを追加。
- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する挙動を採用。
- 設定管理
  - kabusys.config.Settings: 環境変数/.env/.env.local からの設定読み込みとバリデーションを提供。  
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）検出時に行う。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 各種必須キー取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）とデフォルト値を定義。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの値検証を実装。
- ポートフォリオ構築ユーティリティ (kabusys.portfolio)
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装。
  - position_sizing: calc_position_sizes を実装（risk_based / equal / score の allocation をサポート、単元株処理、aggregate cap によるスケーリング）。
  - risk_adjustment: apply_sector_cap（セクター集中除外ロジック）および calc_regime_multiplier（市場レジーム乗数）を実装。
- 研究・リサーチ機能 (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を使用してファクターを算出。
  - feature_exploration: calc_forward_returns, calc_ic (Spearman ランク相関), factor_summary, rank を実装。
  - zscore_normalize を含むエクスポートを提供（kabusys.data.stats から利用）。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む score_news を実装。  
    - 時間ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して使用。
    - バッチ（最大 20 銘柄/コール）、トークン肥大対策、リトライ（429/5xx/タイムアウト等）を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（限定的な DELETE→INSERT）を考慮。
- ユーティリティ
  - utils.process_priority: set_process_priority と set_cpu_affinity を追加。  
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収。権限不足時は警告ログを出してスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite を解析し検証レポートを生成する CLI スクリプトを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力する既定の閾値を持つ。
- パッケージ情報
  - kabusys.__version__ = "0.1.0" を設定。

Changed
- 設定読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される。
- Monitoring の挙動: 監視サービス起動時は常に Settings.sqlite_path（本番用パス）を使用することを明示。
- ExecutionEngine の DB 接続: paper_trading 環境では paper_sqlite_path を使って本番と完全に分離。

Fixed / Improved
- .env パーサーの強化:
  - export KEY=val 形式、シングル/ダブルクォートの中でのバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 無効行・キー無し行の扱いを明確化。
- DuckDB / SQLite の扱いを明確にし、監視テーブル初期化（init_monitoring_db）を冪等に呼ぶようにして起動時のテーブル欠如に耐性を持たせた。
- ロバストネス:
  - run_monitoring のメインループで check_once() が例外を投げてもログ出力して次ループへ継続するように変更。
  - news_nlp の API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行する実装。
  - tools.paper_verification_report はテーブルが存在しないケースを sqlite3.OperationalError でハンドルしデフォルト値を使ってレポートを出力。

Security
- 一部機能（J-Quants、kabu API、OpenAI）の利用には環境変数による API キーが必須:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須取得。未設定時は起動時に ValueError を発生させる。
  - score_news は OPENAI_API_KEY が必要。未設定時は ValueError を送出。
- 外部 API キー等を .env で管理する場合、OS 環境変数が優先され上書き保護される点に注意。

Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - lot_size は現状グローバル固定（関数引数で指定可能）で、将来的に銘柄別 lot_map に拡張する旨の TODO コメントあり。
  - 価格が欠損（0.0）だった場合にセクターエクスポージャーが過少見積りになる可能性があり、前日終値等のフォールバックを検討する TODO が存在。
- process_priority / set_cpu_affinity は権限や OS に依存し、失敗時は警告でスキップする設計。
- news_nlp:
  - レスポンスバリデーションを行うが、部分失敗や API 制限で全コード分のスコアが揃わない場合がある。
  - OpenAI のレスポンス仕様変更に依存するため将来的に変更対応が必要となる可能性あり。
- DuckDB の executemany に関する互換性留意（params が空のときの挙動など）。

Migration / Upgrade notes
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db
- PID / フラグファイルのデフォルト:
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL は整数秒で指定。1 未満や不正値は無視されデフォルト 60 秒にフォールバック。

Acknowledgements
- 本リリースはシステム監視・実行エンジン・ポートフォリオ構築・研究解析・AI ニューススコアリング・ユーティリティ群を含む初期機能群をまとめたものです。

以上。今後のバージョンではテストカバレッジ、エラーハンドリングの強化、銘柄ごとの単元株サポート、API 呼び出しの更なる堅牢化を計画しています。