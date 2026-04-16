Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。

Unreleased
----------

（なし）

0.1.0 - 2026-04-16
-----------------

Added
- プロジェクト初期リリース。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による優雅な終了処理を実装。
    - 監視処理は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（設計上の注意）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db を規定値）を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、エンジンスレッドによる実行、停止フラグ監視、PID ファイル管理を実装。
- 設定/環境読み込み:
  - config.Settings クラスを実装。環境変数から各種設定を取得するユーティリティを提供（DB パス、API キー、監視閾値、環境種別など）。
  - .env / .env.local の自動読み込み機能を追加。OS 環境変数は保護され、.env.local は上書き可能。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースはコメント、export プレフィックス、クォートやエスケープを考慮した堅牢な実装。
  - PAPER_FILL_MODE の検証（instant|partial|never|reject）や KABUSYS_ENV の検証を実装。
- モニタリング DB 初期化:
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルの冪等な初期化を行うようにした。
- ポートフォリオ構築（pure functions）:
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 実際の発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の各割当方法、単元株（lot）丸め、aggregate キャップとスケーリングロジックを含む。
- リサーチ/特徴量:
  - research.factor_research: momentum / volatility / value ファクター計算の実装（DuckDB を受け取り prices_daily / raw_financials を参照）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）と ranking / 統計サマリー（factor_summary）。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- AI ニュース NLP:
  - ai.news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントスコアを計算・ai_scores に書き込む処理を実装。
  - ニュース取得ウィンドウ計算（calc_news_window）、バッチ送信（最大 20 銘柄）、トークン肥大化対策（記事件数・文字数制限）、レスポンス検証、スコアの ±1.0 クリップ、429/5xx/タイムアウトに対する指数バックオフ・リトライを実装。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定必須。
- ツール:
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し PASS/FAIL 判定を出力。各種閾値はスクリプト内で定義（稼働率 99%、成功率 90% 等）。
- ユーティリティ:
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足や未対応 OS は警告ログを出すフェールセーフ。
- DB / クエリエンジン:
  - DuckDB を分析用途に採用（各種研究・AI モジュールで利用）。sqlite3 は runtime/monitoring/実行用データ保持に使用。
- パッケージ初期化:
  - kabusys.__init__ にバージョン情報（0.1.0）と主要パッケージの __all__ を追加。

Changed
- 監視の動作に関する設計上の注記を明示:
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データの一元管理のため）。
- .env 自動ロードの挙動:
  - OS 環境変数を保護するため .env 読み込み時に既存環境変数を上書きしない（ただし .env.local は override を許可し、既存 OS 変数は保護）。

Fixed
- （初版のため特定のバグ修正履歴はなし。設計上の注意点と TODO を README/コード内に明記。）

Notes / Known issues
- ai.news_nlp 実装の途中や今後の注意点:
  - 大量のテキストを API に渡す設計のためトークン制限・コストに注意。記事のトリムやバッチサイズは定数で制御している。
  - OpenAI のレスポンス仕様に依存するためレスポンスバリデーションを厳格に行っているが、外部 API の変更時には調整が必要。
- price が欠損（0.0）の場合の挙動:
  - position_sizing.apply と apply_sector_cap 内で price が欠損だとエクスポージャーやシェア計算が過少見積りになる可能性がある旨を TODO コメントで残している。将来的には前日終値や取得原価でのフォールバックを検討。
- プロセス優先度 / CPU affinity:
  - 権限不足や未対応プラットフォームでは警告を出してスキップする実装。意図した優先度設定が行われない場合は環境（権限・プラットフォーム）を確認すること。
- Paper Trading 環境:
  - paper_trading は本番 DB と分離される設計（PAPER_TRADING_SQLITE_PATH）。paper_trading 用 MockBroker の振る舞いや fill モードは PAPER_FILL_MODE で制御される（入力値検証あり）。
- DB スキーマ依存:
  - research / ai / tools のクエリは prices_daily / raw_financials / raw_news / news_symbols / trade_logs / system_status 等のスキーマに依存する。スキーマが存在しない場合は生成・マイグレーションが必要。
- ドキュメント参照:
  - PortfolioConstruction.md や StrategyModel.md 等の設計ドキュメントに準拠して実装している箇所が多く、実務運用時はこれらのドキュメントを参照すること。

Security
- OpenAI API キー等の機密情報は環境変数で管理すること（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- .env ファイル自動ロードはデフォルトで有効だが、CI/テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化できる。
- .env ローダは OS 環境変数を上書きしない（保護）ため、機密情報を OS 環境に置く運用が混在している場合でも安全に扱えるよう配慮している。

Contributing
- バグ修正・機能追加は PR を通じて行ってください。コードベースにはいくつかの TODO/改善点コメントが残っています（price フォールバック、lot_size の銘柄別化等）。

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。）