# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
慣例: 変更は分類（Added, Changed, Fixed, Removed, Security, Deprecated）して記載します。

なお、本 CHANGELOG の内容は提供されたコードベースから推測して記載しています（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV により挙動変更）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理（環境変数）の強化
  - config.py: .env/.env.local の自動ロード機能を実装（プロジェクトルート検出を行い、OS 環境変数を保護して上書き制御可能）。エクスポート形式やクォート文字列、インラインコメントに対応するパーサを実装。
  - Settings クラスを追加し、各種環境変数（DB パス、PID/KILL ファイルパス、閾値、PAPER_FILL_MODE 等）をプロパティとして提供。
- 監視・実行のための DB 初期化整備
  - monitoring_db.init_monitoring_db を利用して監視テーブルの冪等初期化を行う（run_execution/run_monitoring）。
- Execution 周りの組み立て
  - ExecutionEngine の起動ロジック（ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、RiskConfig/EngineConfig の既定値適用）。
  - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用の SQLite DB に記録する分離方針を採用。
- ポートフォリオ構築関連（純粋関数）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、重み計算（等金額・スコア加重）を実装。スコア全てが 0 の場合は等重フォールバック。
  - portfolio.risk_adjustment: セクター上限フィルタ（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 複数配分方式（risk_based / equal / score）に対応した株数算出ロジックを実装。単元株丸め、1銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を考慮した保守的なコスト見積りと端数処理を組み込む。
- リサーチ機能（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（prices_daily / raw_financials を参照）。MA200、ATR20、各種リターンを SQL + Python で計算。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリを実装。外部ライブラリに依存しない実装。
  - research.__init__ によりエクスポートを整理（zscore_normalize を含む）。
- ニュース NLP（AI）モジュール
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込むフローを実装。バッチ化（最大 20 銘柄/回）、トークン量制限（記事数/文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象コードに限定した DELETE/INSERT）などを備える。OpenAI API キー必須（引数または環境変数 OPENAI_API_KEY）。
- ユーティリティ
  - utils.process_priority: cross-platform（Windows / POSIX）でのプロセス優先度設定と CPU affinity 固定機能を実装。権限不足や未サポート OS では警告を出してスキップする安全設計。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し Pass/Fail 判定を行う（閾値と出力フォーマットを定義）。日付フィルタや DB パス（--db / PAPER_TRADING_SQLITE_PATH）対応。
- パッケージ情報
  - __init__.py による package version 定義（__version__ = "0.1.0"）および主要サブパッケージのエクスポート整理。

### Changed
- 実行時のプロセス優先度設定を起動直後に行うように統一（run_execution, run_monitoring）。権限がない場合は警告ログで継続。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を監視用に使用する方針を明記（監視は本番を前提）。
- run_execution は paper_trading モード時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番と完全に分離する挙動を明確化。

### Fixed / Robustness
- .env パーサが export プレフィクス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行スキップなどに対応し、現実的な .env の記入スタイルに耐えるように改良。
- DuckDB/SQLite 接続は使用後に必ず close するように try/finally で管理（run_execution/run_monitoring）。
- position_sizing の aggregate scaling ロジックで lot 単位の丸め、残余キャッシュによる追加配分を安全に行う実装により、available_cash を超えない配分を保証。
- news_nlp: API レスポンスバリデーションと部分的な失敗からの保護（成功したコードだけ書き換える）を実装。

### Security
- ai.news_nlp は OpenAI API キーの未設定時に明示的にエラーを返す。環境変数名（OPENAI_API_KEY）をドキュメント化。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数を保護するための protected 機構を採用。

## [0.1.0] - 2026-04-11
初回公開リリース（推定）。上記機能の多くがこのバージョンに含まれる想定。

### Added
- 基本的なフレームワーク実装:
  - Execution エンジン起動・実行フロー、Order 管理、Risk 管理（RiskConfig）等のコア実装を含む起動スクリプト群。
  - 監視（SystemMonitor）起動スクリプトと監視用 DB 初期化。
  - 設定管理（Settings）、.env 自動ロード、および主要な環境変数／デフォルト設定。
  - ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限・レジーム乗数）。
  - リサーチ（ファクター計算、将来リターン、IC、統計サマリ）。
  - ニュース NLP（OpenAI 経由のセンチメントスコアリング）および Paper Trading 検証レポートツール。
  - プロセス優先度・CPU affinity 設定ユーティリティ。
- DuckDB を用いたリサーチ処理、SQLite による監視・paper_trading データ保存。

### Changed / Fixed
- 初期実装のため、各コンポーネントは今後の改善・リファクタリングの余地あり（API の安定化、エラーハンドリング、テスト追加 等）。

---

参照:
- 重要な環境変数: KABUSYS_ENV, SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, MONITOR_POLL_INTERVAL, OPENAI_API_KEY, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH など。
- Paper Trading と Live のデータ分離は設計上重視されています。監視は本番 DB を参照する点に注意してください。

（以上）