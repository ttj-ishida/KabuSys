Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースの内容から推測して作成しています。実際のリリース履歴と差異がある可能性があります。

フォーマットの説明
- 本ファイルは Keep a Changelog の形式に準拠しています。
- セマンティックバージョニング (MAJOR.MINOR.PATCH) を想定しています。

Unreleased
---------
- 既知の改善点 / TODO（今後のバージョンで対応予定）
  - portfolio.risk_adjustment.apply_sector_cap:
    - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、前日終値や取得原価などのフォールバック価格を使う拡張を検討中。
  - portfolio.position_sizing:
    - 銘柄ごとの lot_size をサポートするため、将来的に stocks マスタから lot_size を取得する設計への拡張を予定。
  - ai.news_nlp.score_news:
    - API 呼び出し失敗時に一部チャンク処理が失敗しても他の銘柄スコアを保護する実装になっているが、さらにロバストな部分再試行／部分コミット戦略を改善予定。
  - duckdb に対する executemany の扱い（空パラメータ回避）など、DB 周りの堅牢化を継続的に改善予定。

[0.1.0] - 2026-04-13
--------------------
Added
- 初回リリース（0.1.0）。以下の主要機能およびモジュールを追加。
- コア / 設定
  - kabusys.config.Settings: 環境変数ベースの設定取得クラスを追加。必須値チェックや値検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - .env 自動ロード機能: プロジェクトルート (.git または pyproject.toml を起点) を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。export 形式、クォート／エスケープ、インラインコメント等に対応したパーサを実装。
  - デフォルトパスの提供: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等のデフォルト値を設定。

- 実行スクリプト / ランタイム
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBrokerClient（BrokerClientFactory による切替）を使用し、Paper Trading 用の専用 SQLite（data/paper_trading.db 等）へ記録して本番 DB と分離。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで構成。初期ポートフォリオ値は broker.get_available_cash() から取得。
  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する実装。

- 監視 / ツール
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を実行開始時に呼び出して監視テーブルの存在を保証。
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。コマンドラインから期間指定可能（--from, --to, --db）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を行う。閾値と出力フォーマットを定義。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルからスコア降順で候補を選択（signal_rank によるタイブレークを実装）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを追加。既存保有を考慮して上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（デフォルト・フォールバックを含む）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算機能を追加。allocation_method ("risk_based","equal","score") をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer の考慮、残差配分ロジック等を実装。

- 研究 / データ処理
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials テーブルを参照し、モメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 各関数はデータ不足時に None を返す等、堅牢な計算ロジックを実装。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損や ties を扱う）。
    - factor_summary, rank: ファクター統計サマリー、ランク変換ユーティリティを提供。
  - research パッケージは kabusys.data.stats.zscore_normalize を再エクスポート。

- AI / NLP
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して銘柄別スコアを ai_scores テーブルに書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1 クリッピング、部分置換（DELETE + INSERT）による安全な書き込み戦略を採用。
    - ニュース収集ウィンドウ計算（JST 基準 -> UTC 変換）を提供。

- ユーティリティ
  - utils.process_priority:
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、nice 値・Windows の優先度クラスを適用。失敗時は警告ログでスキップ。
    - set_cpu_affinity: CPU affinity を最初の N コアに固定する機能を追加（アクセス権限エラー時は警告でスキップ）。

Changed
- パッケージ情報
  - パッケージトップレベルに __version__ = "0.1.0" を設定。

Fixed
- ロバスト性向上
  - run_monitoring.run_loop: check_once() 実行時の例外を捕捉してループを継続するように変更（監視プロセスの安定化）。
  - 環境変数パース: export 形式やクォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善して .env 読み込みの堅牢性を向上。

Notes
- 環境変数の主要項目（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY
  - KABUSYS_ENV (development | paper_trading | live)
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等

- DB
  - DuckDB を分析処理（prices_daily, raw_financials 等）に使用。実行時は duckdb_path を指定可能。
  - 監視・発注ログ等は SQLite（monitoring.db / paper_trading.db）で管理。

- 安全設計
  - Paper Trading 環境は本番 DB と分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
  - ai.news_nlp は API キー未設定では明示的なエラーを返す。

Security
- 本リリースで特記すべきセキュリティ修正はありません。OpenAI API キー等の機密は環境変数で管理することを想定しています。

開発者向け補足
- .env 自動読み込みはプロジェクトルートが見つからない場合はスキップされます。CI/テスト環境で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のスキーマ初期化（init_monitoring_db 等）は起動時に呼び出して冪等性を確保しています。

----- end of CHANGELOG -----