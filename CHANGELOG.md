KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

格式: Keep a Changelog — 日本語訳

0.1.0 - 2026-04-13
-----------------
Added
- 初回リリースとして主要機能を追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して Broker のモック運用が可能（データは data/paper_trading.db に分離）。起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番の sqlite_path を使用する仕様。
  - 設定管理
    - config.Settings: 環境変数 / .env ファイル読み込みユーティリティを実装。プロジェクトルート（.git または pyproject.toml）を基に自動で .env / .env.local を読み込み（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。複数の設定プロパティを追加（duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path 等）および env/log_level 検証。
    - .env パーサーは export 形式や引用符・エスケープ、インラインコメント処理に対応。
  - 監視 DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルの存在を保証（冪等）。
  - 実行系コンポーネント（Execution）
    - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を組み合わせて実運用セッションを起動するワークフローを追加。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, circuit breaker 等）を実装し、初期ポートフォリオ値に broker.get_available_cash() を使用。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を追加。スコア全0時のフォールバック挙動（等金額）をログ出力。
    - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を追加。unknown セクターの扱い、レジーム未定義時のフォールバックを明記。
    - portfolio.position_sizing: 発注株数決定ロジックを追加。allocation_method ("risk_based", "equal", "score") に対応、lot_size（単元）丸め、コストバッファ考慮の aggregate cap スケーリングロジックを実装。
  - リサーチ機能（DuckDB ベース）
    - research.factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算を追加（calc_momentum, calc_volatility, calc_value）。DuckDB のウィンドウ関数を利用し、欠損やウィンドウ未満時の扱いを考慮。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、rank / factor_summary 等の統計ユーティリティを追加。外部ライブラリに依存せず実装。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む処理を追加。処理はチャンク (最大 20 銘柄/リクエスト)、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1 にクリップする等の耐障害性を持つ。ニュース集計ウィンドウ計算関数 calc_news_window を提供。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度 (set_process_priority) と CPU affinity (set_cpu_affinity) を設定するユーティリティを追加。権限不足等の失敗は警告ログでスキップ。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、API レイテンシ（P95）等を計算して PASS/FAIL を判定する閾値を定義。コマンドラインから期間フィルタおよび DB パス指定が可能。

Changed
- パッケージレイアウトとエクスポートを整理
  - kabusys.__init__.py にバージョン文字列 __version__="0.1.0" を追加し、主要サブパッケージ名を __all__ で公開。
  - kabusys.portfolio と kabusys.research の __init__ で主要 API を再エクスポートし、import の利便性を向上。

Fixed
- 環境読み込みの堅牢性向上
  - .env 読み込みでファイルオープン失敗時に warnings.warn を出すようにして無視できるようにした。
- ポジションサイズ計算での端数処理や aggregate scale-down のアルゴリズムを実装し、手数料/スリッページの見積り（cost_buffer）を考慮するよう改善。

Notes / Behavioural details / Migration
- 設定の自動ロード
  - デフォルトでプロジェクトルートから .env/.env.local を自動ロードします。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で指定可能。整数で 1 以上を期待し、不正値や 0/負値はデフォルト 60 秒にフォールバックします。
- 監視 DB の取り扱い
  - run_monitoring は環境にかかわらず settings.sqlite_path（本番想定）を使用します。paper_trading 用に分離した DB を使用したい場合は run_execution 側の paper_sqlite_path を使用する等、用途ごとに DB を選択してください。
- OpenAI API
  - ai.news_nlp.score_news は API キーが必須。api_key 引数または環境変数 OPENAI_API_KEY を指定してください。API 呼び出し失敗時はログ出力のうえ可能な範囲で処理を継続するフェイルセーフ設計です。
- 互換性
  - 既存の設定キーの検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）が追加され、無効値は ValueError を投げます。CI / デプロイ環境でこれらの環境変数の値を確認してください。

Security
- OpenAI API キー等、機密情報は .env や環境変数で管理してください。Settings は OS 環境変数を保護するため .env 読み込み時に既存の OS 環境変数を上書きしないデフォルト挙動（.env.local は override=True だが protected により OS 変数は保護）を採用しています。

Acknowledgements
- このリリースはシステム監視、実運用エンジン、ポートフォリオ構築、研究用ファクター計算、ニュース NLP の各機能を最初にまとめたものです。今後はテスト、ドキュメント、例外処理の拡充、性能最適化を継続して行います。