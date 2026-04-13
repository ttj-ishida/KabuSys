# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- 起動スクリプトを追加・整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db 等）と MockBrokerClient を使用して本番 DB と分離。
- 設定管理
  - config.py: .env/.env.local の自動ロード機能を実装（OS環境変数を保護）。.env パースの堅牢化（クォート、エスケープ、コメント対応）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - Settings クラスを導入し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH、閾値設定など）をプロパティ経由で取得・検証するようにした。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・同点のタイブレーク）と重み計算（等配分・スコア加重）。スコアが全て 0 の場合は等配分にフォールバックする警告あり。
  - portfolio/position_sizing.py: position sizing 実装（risk_based / equal / score）。単元株丸め、個別上限・合算上限（available_cash）を考慮したスケーリング、cost_buffer を使った保守的見積り、lot 単位での端数処理を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。unknown セクターの扱い、ログ出力、未知レジームのフォールバックを含む。
- リサーチ（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して各種指標（mom_1m/3m/6m、MA200乖離、ATR20、avg turnover、PER/ROE 等）を計算。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリー、安定したランク付け関数を実装。外部ライブラリに依存せず標準ライブラリのみで計算。
  - research パッケージの public API を __init__ で整理。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini 想定）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。API バッチサイズ、トークン肥大対策（max articles / max chars）、429/ネットワーク/5xx に対するエクスポネンシャルバックオフ、レスポンスバリデーション、スコアの ±1.0 クリップを行う。記事対象ウィンドウ計算（JST→UTC 変換）ロジックを提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はファイル内定義）する。コマンドライン引数で期間・DB パス指定が可能。欠損テーブルに対して堅牢に動作する設計。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows と POSIX を吸収）と CPU affinity 設定ユーティリティを追加。プラットフォーム未対応時やアクセス権限不足時は警告を出してスキップ。
- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの存在を保証し冪等に初期化する処理を実装（起動スクリプト内で使用）。

### Changed
- 環境に応じた DB 選択ロジックを明確化
  - run_execution: paper_trading 環境では paper_sqlite_path を使用し、本番 SQLite と明確に分離。
  - run_monitoring: 監視系は環境にかかわらず本番 sqlite_path を使用する旨を明示（監視データは本番 DB へ）。
- 設定値バリデーション強化
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など不正値に対する検証を追加し、誤設定時に早期に例外を投げるようにした。

### Fixed
- .env パーサの改善により、クォート・エスケープやインラインコメントの扱いでの不正な解釈を修正（既存の環境変数保護ロジックと併用）。
- レポート / 統計計算のヌル安全性を向上（データ不足時に None/N/A を返す、sqlite3.OperationalError をハンドリング）。

### Notes
- 一部機能に TODO / 将来の拡張コメントあり（例: 単元株 lot_size の銘柄別対応、position_sizing の価格フォールバック戦略など）。
- OpenAI API を利用する機能は実行時に API キー（OPENAI_API_KEY）を必要とし、API 利用時の課金やレート制限に注意してください。

---

## [0.1.0] - 2026-04-13

初回リリース（コードベースのスナップショットに基づく推定） — 基本機能の提供。

### Added
- コア機能
  - 自動売買プラットフォームの核となるモジュール群を導入:
    - execution: ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager、BrokerClientFactory（paper_trading に対する Mock ブローカーを含む想定）
    - monitoring: SystemMonitor と監視用 DB 初期化ロジック
    - portfolio: 候補選定、重み計算、ポジションサイズ計算、リスク調整（セクターキャップ・レジーム乗数）
    - research: ファクター計算（モメンタム／ボラティリティ／バリュー）、特徴量探索（将来リターン・IC・統計サマリー）
    - ai: ニュース NLP スコアリング（OpenAI 連携の基礎）
    - tools: Paper Trading 検証レポート生成スクリプト
- 設定とユーティリティ
  - Settings クラス、.env 自動ロード、環境変数の厳密検証
  - process priority / CPU affinity 設定ユーティリティ
- DB/ストレージ
  - DuckDB をリサーチ用に使用（prices_daily / raw_financials 参照）
  - SQLite を監視・paper_trading 用に使用（監視・トレードログ等）

### Changed
- N/A（初版のため過去変更なし）

### Fixed
- N/A（初版のため過去修正なし）

---

参照:
- プロジェクトバージョンは kabusys.__init__.__version__ = "0.1.0" に基づく初期バージョン推定です。