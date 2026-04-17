CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。形式は "Keep a Changelog" に準拠しています。

フォーマット:
- 重大度順: Added / Changed / Fixed / Deprecated / Removed / Security
- バージョン見出しの形式: ## [バージョン] - YYYY-MM-DD

## [Unreleased]

- 次回リリース用の作業中の変更はここに記載してください。

## [0.1.0] - 2026-04-17

Added
-----
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じてペーパートレード用 DB を分離して利用（KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: .env 自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml）。ロード順序は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを提供。多数のプロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）を環境変数から取得。PAPER_FILL_MODE のバリデーションを実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: BUY シグナルの候補選定（select_candidates）、等金額配分・スコア配分（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合に等配分へフォールバックする警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算（calc_position_sizes）を追加。risk_based / equal / score の配分方式、単元株丸め、aggregate cap（スケールダウン）や cost_buffer を考慮した実装を含む。
- 研究・リサーチ
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルを参照。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・統計サマリ（factor_summary）・ランク変換（rank）を実装。外部依存を避け標準ライブラリのみで実装。
  - research/__init__.py で主要関数をエクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI (gpt-4o-mini) でスコアリングし ai_scores テーブルへ書き込む処理を追加。バッチ処理（最大 20 銘柄/コール）、トークン肥大対策、エクスポネンシャルバックオフによる再試行、レスポンス検証、スコアクリップ（±1.0）などの設計を実装。ニュース収集ウィンドウ計算ユーティリティ (calc_news_window) を提供。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX (Linux, Darwin, FreeBSD) を考慮した実装で、権限不足や未対応 OS の場合は警告ログを出してスキップする。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。コマンドラインから期間指定可能（--from, --to, --db）。稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を計算し PASS/FAIL 判定を出力。閾値（例: 稼働率 99% など）を定義。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。主要サブパッケージを __all__ に定義。

Changed
-------
- 初期リリースのため特記すべき既存からの変更点はありません（新規追加中心）。

Fixed
-----
- 各モジュールで実運用を想定した堅牢性処理を追加:
  - .env 読み込みで I/O エラー発生時に warnings.warn で通知して処理を継続。
  - .env パーサで引用符・バックスラッシュエスケープ・インラインコメントの扱いを細かく実装。
  - position_sizing や apply_sector_cap で価格欠損時にスキップするようにして不正発注を防止するガードを追加。
  - calc_score_weights は全スコアがゼロの場合に等分配へフォールバックし、警告ログを出すようにして例外発生を防止。

Known issues / Limitations
--------------------------
- run_monitoring は「監視」用途の DB として常に settings.sqlite_path（本番用 monitoring.db）を使用する設計になっているため、KABUSYS_ENV=paper_trading を指定しても監視 DB は分離されない点に注意。これは設計の意図的仕様だが、用途によっては混同の原因となる。
- ai/news_nlp.py は設計が詳細に記載され、主要なユーティリティ（calc_news_window ほか）を実装しているが、スニペット末尾で処理の一部が切れている（スニペット最後が中断）ため、完全な I/O / DB 書き込みルートは実装時に要確認。
- apply_sector_cap 内で price_map に価格が欠損（0.0）だとエクスポージャーが過小見積もりされる旨の TODO コメントあり。将来的に前日終値等のフォールバックが推奨される。
- set_process_priority / set_cpu_affinity は権限や OS サポート状況により失敗する可能性があり、その場合は警告ログを出してスキップする挙動。

Migration notes / 運用時の注意
-----------------------------
- 環境変数
  - KABUSYS_ENV: "development" | "paper_trading" | "live" のいずれかを設定。無効な値は例外になる。
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）。整数かつ 1 以上を推奨。
  - PAPER_FILL_MODE: paper trading の MockBrokerClient の挙動 ("instant" | "partial" | "never" | "reject")。無効な値は ValueError。
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB のパス（--db オプションや環境変数で変更可能）。
  - DUCKDB_PATH / SQLITE_PATH: デフォルトは data/kabusys.duckdb / data/monitoring.db。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを抑止できる（テスト等で有用）。
  - OPENAI_API_KEY は ai/news_nlp の実行時に必要（引数経由でも指定可能）。未設定の場合は ValueError を送出。
- ファイルフラグ
  - 停止制御に data/stop_requested.flag や data/execution.pid 等のファイルを利用する（run_* スクリプトで参照）。
- 権限
  - プロセス優先度設定は psutil の操作権限が必要。アクセス拒否時はログ警告で続行する。

Security
--------
- OpenAI API キー等の機密情報は .env か環境変数で管理すること。自動 .env ロードは OS 環境変数を保護するために既存のキーを上書きしない（.env.local は override=True だが protected により OS 環境は保護される）。

参考: コマンドライン例
---------------------
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

以上。