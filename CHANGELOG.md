CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- (なし)

0.1.0 - 2026-04-12
------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加しました。
  - 実行・監視用エントリポイント
    - run_execution.py
      - ExecutionEngine の起動スクリプト。
      - 起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
      - DuckDB 接続を用いて分析用 DB を利用。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
      - RiskConfig のデフォルト値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を提供。initial_portfolio_value はブローカから取得。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、0 以下はデフォルトにフォールバックして警告を出力）。
      - 監視用途の SQLite は環境にかかわらず本番 sqlite_path を使用する実装（paper_trading 環境でも監視は本番 DB を参照する点に注意）。
      - 起動時にプロセス優先度を "high" に設定。

  - 設定・環境変数管理
    - config.py
      - プロジェクトルートを .git または pyproject.toml で自動検出し、.env / .env.local を自動読み込み（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサは export 形式、クォート（シングル/ダブル）とエスケープ、インラインコメント処理に対応。
      - Settings クラスで各種設定値をプロパティとして提供（パス、閾値、API トークン等）。入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実施。
      - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db, PID_FILE_PATH=data/execution.pid, KILL_FLAG_PATH=data/kill.flag。

  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
      - calc_equal_weights, calc_score_weights: 等金額とスコア加重。全スコアが 0 の場合は等金額にフォールバックして警告。
    - portfolio.risk_adjustment
      - apply_sector_cap: 既存保有・価格情報に基づきセクター集中を制限（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime('bull'|'neutral'|'bear') による投下資金乗数（デフォルト値と unknown 時のフォールバック動作）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method により株数を計算（risk_based / equal / score）。
      - 単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリング、端数配分ロジック（fractional remainders に基づく追加配分）を実装。

  - リサーチ / ファクター計算
    - research.factor_research
      - calc_momentum, calc_volatility, calc_value: DuckDB (prices_daily, raw_financials) を参照してモメンタム / ボラティリティ / バリュー系ファクターを計算。ウィンドウ不足時の None 処理やパフォーマンスを意識したスキャン範囲を実装。
    - research.feature_exploration
      - calc_forward_returns: 将来リターン（任意ホライズン）の計算（horizons の検証あり）。
      - calc_ic: Spearman ランク相関（IC）実装。データ不足時は None。
      - rank, factor_summary: ランク付け（同順位は平均ランク）と統計サマリ。

  - AI ニュース NLP
    - ai.news_nlp
      - raw_news を OpenAI (gpt-4o-mini) でスコアリングして ai_scores テーブルへ書き込み。
      - タイムウィンドウ計算（target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う）、記事集約、1 銘柄あたりの文字数/記事数制限、最大バッチサイズ、チャンク化、429/5xx/タイムアウトに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップなどを実装。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時はエラー。

  - ユーティリティ
    - utils.process_priority
      - プラットフォーム非依存でプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）、および set_cpu_affinity（最初の N コアに固定）を提供。psutil で可能な限り設定し、権限不足や未サポート環境では警告してスキップ。

  - CLI ツール
    - tools.paper_verification_report
      - Paper Trading 用検証レポート生成ツール。コマンドライン引数 --from / --to / --db をサポートし、system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（P95 を含む）を集計して PASS/FAIL 判定を行う。各種閾値はファイル内で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。

  - パッケージ情報
    - __init__.py にてバージョンを "0.1.0" に設定。

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Security
- OpenAI API キーなどの機密情報は Settings / 環境変数から取得し、.env 自動読み込みは OS 環境変数を保護する設計（.env.local は override 可能だが OS 環境変数は上書きされない）。

Notes / 注意事項
- run_monitoring は監視用 DB に settings.sqlite_path（本番想定）を必ず使用します。paper_trading 環境で監視だけ切り離したい場合は構成に注意してください。
- .env 自動ロードはプロジェクトルート検出に依存しており、ルートが見つからない場合はスキップされます。
- position_sizing の lot_size は将来的に銘柄別に拡張する余地を残しています（TODO コメントあり）。
- DuckDB の executemany に関する制約を考慮した実装上の注意（ai.news_nlp 内のデータ置換ロジックやその他箇所のコメント参照）。

今後の予定（例）
- 単体テスト・統合テストの追加（特に position sizing と aggregate cap ロジック、ai/news_nlp の API エラーハンドリング）。
- 銘柄別 lot_size の導入、価格フォールバック（price_map が欠損時の補完値）などの改善。
- モニタリング/監査用のログ拡充とメトリクス出力（Prometheus 等）への対応。