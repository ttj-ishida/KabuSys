CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
---------

Added
- 実行用スクリプトを追加:
  - run_execution.py — ExecutionEngine を起動するエントリポイントを提供。環境に応じて paper_trading 用 DB を分離して使用する（KABUSYS_ENV=paper_trading の場合は paper DB を使用し、MockBrokerClient を経由して処理）。
  - run_monitoring.py — SystemMonitor のポーリングループを起動するエントリポイントを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- ポートフォリオ構築ライブラリを追加:
  - portfolio.portfolio_builder — シグナル選定（スコア降順/タイブレーク）、等金額配分・スコア加重配分を提供。
  - portfolio.position_sizing — 複数の配分方式（risk_based / equal / score）に基づく発注株数の算出、単元株（lot_size）丸め、aggregate cap によるスケールダウンを実装。
  - portfolio.risk_adjustment — セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- リサーチ／ファクター計算機能を追加:
  - research.factor_research — DuckDB を利用したモメンタム／ボラティリティ／バリュー系ファクターのバッチ計算（MA200、ATR20、リターン等）。
  - research.feature_exploration — 将来リターン計算、IC（スピアマンランク相関）計算、ファクター統計サマリ、ランク計算ユーティリティを提供。外部ライブラリに依存せず純粋 Python と DuckDB で実装。
- ニュース NLP スコアリングモジュールを追加:
  - ai.news_nlp — raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）にバッチリクエストし、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理を実装（バッチサイズ、トークン肥大化対策、レスポンス検証、スコアクリップ、リトライ方針を備える）。
- ツール類を追加:
  - tools.paper_verification_report — Paper Trading の履歴 DB から稼働率、注文成功率、レイテンシなどを集計して検証レポートを出力する CLI。閾値による PASS/FAIL 判定を実装。
- 設定／環境読み込みの強化:
  - config.Settings: .env/.env.local の自動読み込み（プロジェクトルート検出: .git / pyproject.toml を探索）、.env の詳細パース（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化が可能。
  - 多数の設定プロパティを追加（DB パス、paper_trading 用パス、PID/KILL ファイルパス、閾値等）と入力検証（有効値チェック）を実装。
- プロセス制御ユーティリティ:
  - utils.process_priority — クロスプラットフォームでプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。権限不足や未対応プラットフォーム時に安全にスキップするロバストネスを実装。
- DB 初期化ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

Changed
- ExecutionEngine の起動フローの明確化:
  - 起動直後にプロセス優先度を high に設定する処理を追加。
  - paper_trading 環境では paper 用 SQLite を使用して本番 DB と分離。
  - duckdb の接続を受け渡して研究/集計処理と共用できる設計。
- ポジションサイズ計算の挙動改善:
  - cost_buffer を考慮した保守的なコスト見積り、aggregate cap によるスケールダウン、lot_size（単元）単位での丸めと残余配分ロジックを実装。
- セクター上限チェックの挙動改善:
  - 既存保有のうち「当日売却予定銘柄」をエクスポージャー計算から除外するオプションを追加。
  - sector が不明 ("unknown") な場合は上限適用対象外とする挙動を明確化。

Fixed
- .env の読み込みに関する堅牢性強化:
  - ファイルが読み込めない場合に warnings.warn を出し安全に継続するように変更。
  - OS 環境変数を保護する protected セットを導入して .env.local による不慮の上書きを回避。
- DuckDB / SQLite クエリでの NULL / データ不足ハンドリングを改善:
  - ファクター計算やレポート生成でデータ不足（行数不足／NULL 値）が発生した場合に None を返すなど、安全に処理を続行するように調整。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決し、未設定の場合は明示的に例外を発生させることで不正使用や隠れた挙動を防止。

0.1.0 - 2026-04-13
------------------

Added
- 初期リリース: 基本的な自動売買・研究・監視の骨格を実装。
  - 実行エンジン、注文管理、リスク管理、リコンシリエーション（Reconciler）等の主要コンポーネント（ExecutionEngine 周り）。
  - 監視用 SystemMonitor と monitoring DB 初期化ユーティリティ。
  - ポートフォリオ構築（選定・重み付け・株数算出）とリスク調整（セクター上限・レジーム乗数）。
  - リサーチ用のファクター計算（モメンタム・ボラティリティ・バリュー）と調査ユーティリティ（IC・統計サマリ）。
  - ニュース NLP（OpenAI を利用したセンチメントスコアリング）の基盤実装。
  - ツール: Paper Trading 用検証レポート出力スクリプト。
  - 設定管理: .env 自動読み込み・厳密なパースと Settings クラス。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。

Changed
- パッケージバージョンを 0.1.0 に設定。

Notes / Known issues
- 一部のモジュールは外部サービス（ブローカークライアント、OpenAI 等）に依存します。実運用では適切な API キーや接続先の設定（.env）を行ってください。
- DuckDB / SQLite のスキーマ整備（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status 等）が前提になります。ツール・リサーチ機能を利用する前に DB の準備が必要です。

ライセンスや貢献方法、詳細な実装ドキュメントはプロジェクトの README や各モジュールの docstring を参照してください。