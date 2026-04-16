CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースから推測したリリース日（2026-04-16）を使用しています。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-16
-------------------

Added
- パッケージ初期バージョンを追加
  - パッケージメタデータ: kabusys.__version__ = "0.1.0"
- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - 環境に応じた SQLite パス切替（KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用）。
    - BrokerClientFactory を利用したブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の組み立てと ExecutionEngine の起動/停止制御を実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の管理をサポート。
    - プロセス優先度を設定（set_process_priority("high")）。
    - duckdb 接続の利用（分析用 DB）。
- 監視用エントリポイント
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の設計。
    - 停止フラグ検知でループ終了（data/stop_requested.flag）。
    - プロセス優先度設定、sqlite3 / duckdb 接続管理、例外安全なループ処理を実装。
- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と挙動（OS 環境変数保護、override の制御）。
    - 複雑な .env 行パース（export プレフィックス、クォート、エスケープ、インラインコメント処理）を実装。
    - Settings クラスを導入し、各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境判定など）。
    - 必須環境変数未設定時に _require() で明確なエラーを出す。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を追加。
    - スコアが全てゼロの場合のフォールバック（等分配）と警告ログ。
  - portfolio.risk_adjustment
    - セクター集中制限 (apply_sector_cap) を実装。既存保有からセクター別エクスポージャ計算、上限超過セクターの除外ロジックを持つ。
    - レジーム乗数 (calc_regime_multiplier)："bull"/"neutral"/"bear" に対応（未知レジームはフォールバック）。
  - portfolio.position_sizing
    - position sizing ロジックを実装（risk_based, equal, score の配分方式に対応）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り。
    - スケーリング後の端数配分ロジック（残余キャッシュを用いて lot 単位で再配分）。
- utils（ユーティリティ）
  - utils.process_priority
    - クロスプラットフォームのプロセス優先度設定（Windows 用 priority class / POSIX 用 nice 値）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - 権限不足や未サポート環境の際は警告を出して安全にスキップ。
- 研究/リサーチ機能
  - research.factor_research
    - Momentum, Volatility, Value などのファクター計算関数を実装（DuckDB 接続を受ける）。
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials を参照して所定の指標を返す。
    - 大規模データスキャンを意識した window/buffer の設計。
  - research.feature_exploration
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ファクター統計サマリ (factor_summary)、rank ユーティリティを実装。
    - Pandas 等に依存せず標準ライブラリで実装。
  - research.__init__ により上記関数と zscore_normalize をエクスポート。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL を判定する。
    - デフォルト DB パス: data/paper_trading.db。コマンドライン引数 --from / --to / --db をサポート。
    - 各種閾値を定義（稼働率 >= 99%、注文成功率 >= 90% など）。
    - SQLite のテーブル欠損時に例外を吸収して N/A 表示にフォールバック。
- AI ニュース NLP（ニュースセンチメント）
  - ai.news_nlp
    - raw_news を集約して OpenAI API (gpt-4o-mini) により銘柄ごとのセンチメントを算出し ai_scores に書き込む処理を設計／実装（部分実装を含む）。
    - ニュース収集ウィンドウ（JST基準の前日15:00〜当日08:30、内部は UTC で扱う）計算ユーティリティ (calc_news_window) を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン膨張対策（記事数/文字数の上限）、API リトライ（指数バックオフ）を設計。
    - 出力 JSON フォーマット検証、スコアの ±1.0 クリッピング、部分成功時のテーブル更新戦略（対象コードのみ上書き）を設計。
    - OpenAI API キーの解決ロジックと未設定時のエラーを実装。
- データベース初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び出すことで監視用テーブルの冪等な初期化を行う（存在確認を保証）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- 外部 API キー（OpenAI など）は環境変数で提供する設計にし、未設定時に明確に失敗するように実装（安全性のための注意喚起）。

注意事項 / 補足
- 環境変数自動ロードはプロジェクトルートを基準に行われるため、パッケージ配布後も .env の自動検出が期待通りに動作しますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- paper_trading 環境は本番 DB と明確に分離される設計（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- News NLP 処理や AI 統合は外部 API 呼び出しを含むため、運用時は API 利用制限／コスト・rate limit ハンドリングに注意してください。
- 一部モジュール（ai.news_nlp の記事集約以降など）はファイル末尾で切れている可能性があるため、実運用前に完全実装と追加テストが必要です。