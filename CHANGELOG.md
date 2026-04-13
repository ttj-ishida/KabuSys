CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に準拠して記載しています。  
日付はリリース日を示します。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。パッケージのバージョンは kabusys.__version__ = "0.1.0" に設定。
- 起動スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB と MockBrokerClient（BrokerClientFactory が解決）を使用して本番 DB と分離する。
- 設定管理:
  - config.py: 環境変数／.env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml で探索）。読み込み優先度は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。.env のパースは引用符、エスケープ、行内コメント等に対応。
  - Settings クラスを提供し、各種設定（DB パス、PID/KILL フラグパス、しきい値や環境判定フラグ等）をプロパティで取得可能に。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV / LOG_LEVEL の値検証を実装。
- 監視 DB 初期化ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルが存在することを保証する処理を追加（冪等）。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。--from/--to/--db オプションをサポートし、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL 判定を出力する。DB が無い場合のハンドリングやテーブル欠損時のフォールバックを実装。
- ポートフォリオ構築:
  - portfolio.portfolio_builder: 候補選定（select_candidates）・等配分（calc_equal_weights）・スコア加重（calc_score_weights）を追加。全スコア 0 の場合に等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中上限を考慮したフィルタ（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加（regime の既定は bull/neutral/bear）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を追加。risk_based / equal / score の allocation_method をサポートし、単元株（lot_size）丸め、per-stock と aggregate の上限、コストバッファを考慮したスケールダウン・端数配分ロジックを実装。
- リサーチ／因子計算:
  - research.factor_research: モメンタム、ボラティリティ、バリュー各ファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB 上の prices_daily / raw_financials を参照して各種ウィンドウ計算を行う。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank/統計サマリ（factor_summary）などを追加。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で主要ユーティリティをエクスポート（zscore_normalize を含む）。
- AI ニューススコアリング:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む機能を追加。銘柄ごと集約、1銘柄あたり記事数・文字数のトリミング、最大バッチサイズ、429/5xx/タイムアウトに対する指数バックオフでのリトライ、レスポンス検証とスコアの ±1.0 クリップを実装。
  - calc_news_window() による JST 時刻ウィンドウ計算を導入（前日15:00 JST〜当日08:30 JST 相当）。
- ユーティリティ:
  - utils.process_priority: cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。権限不足や未対応 OS の場合はワーニングを出してスキップする堅牢性を実装。
- データベース:
  - DuckDB を分析用 DB（デフォルト data/kabusys.duckdb）、SQLite は監視や paper_trading 用（data/monitoring.db, data/paper_trading.db）として導入。デフォルトパスは Settings に定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する実装。未設定時は ValueError を返して安全に停止。

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップする（パッケージ配布後の安全性確保）。
- run_monitoring の監視 DB は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する点に注意。run_execution は paper_trading 環境時に data/paper_trading.db を使用して本番 DB と分離する。
- calc_position_sizes 等は単体関数で副作用がなく、テスト可能な純粋関数群として実装。
- AI スコアリングは部分失敗時に既存のスコア保持を意図して、更新対象コードに対してDELETE→INSERT の方式で置換する設計（部分失敗で他銘柄のデータを失わない工夫）。
- process priority / cpu affinity の設定は権限によって失敗する可能性があるため、例外をキャッチしてワーニングで継続する実装。

今後の予定（短期）
- portfolio.position_sizing の lot_size を銘柄別に持たせる拡張（stocks マスタとの連携）。
- price 欠損時のフォールバック（前日終値や取得原価）を導入してセクターエクスポージャー計算の堅牢化。
- AI スコアリングのエラーハンドリング強化とメトリクス収集。

----- 

この CHANGELOG はコードベースから実装内容を推定して作成しています。さらに詳細な変更履歴（コミット単位やイシュー参照）を希望する場合は、コミットログやリポジトリの履歴からの補完を行います。