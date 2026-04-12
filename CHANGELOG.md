# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の仕様に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 監視・実行系の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイント。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化を行い、本番 sqlite_path を常に使用する挙動を採用。
  - run_execution.py: ExecutionEngine を起動するスクリプト。環境変数 KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（data/paper_trading.db デフォルト）を使用する。ExecutionEngine の組み立て・起動フロー（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を含む。

- ポートフォリオ構築・サイズ決定・リスク調整モジュールを追加
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全てが 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた乗数計算（calc_regime_multiplier）。
  - portfolio.position_sizing: position sizing の実装（calc_position_sizes）。risk_based / equal / score の配分方式をサポート。lot_size（単元）に基づく丸め、aggregate cap によるスケーリング（端数処理の優先配分ロジック含む）、コストバッファ考慮等を実装。

- 研究・ファクター計算モジュールを追加
  - research.factor_research: Momentum / Volatility / Value のファクター計算（DuckDB 接続で prices_daily / raw_financials を参照）。MA200、ATR20、各種モメンタム（1M/3M/6M）等を実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）。
  - research パッケージは zscore_normalize（kabusys.data.stats）を含めてエクスポート。

- AI ニュース NLP スコアリング機能を追加（部分実装）
  - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）を用いセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。バッチ処理、トークン肥大化対策（最大記事数・最大文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング（±1.0）等をサポート。
  - calc_news_window, score_news 等のユーティリティを提供。

- 運用用ユーティリティを追加
  - utils.process_priority: プロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収し、アクセス権限不足などの例外は警告を出して安全にスキップ。

- 設定管理・.env 自動読み込みを実装
  - config.Settings: 環境変数をラップしたプロパティ群を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、閾値等）。.env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）を行い、OS 環境変数を保護する挙動を採用。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の値検証を実装。

- 運用支援ツールを追加
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計し、PASS/FAIL 判定を出力。日付フィルタと DB パス指定オプションを提供。

- パッケージメタ情報
  - パッケージバージョンを 0.1.0 に設定（kabusys.__init__.__version__）。

### Changed
- DuckDB をデータ解析・ファクタ計算の標準 DB として利用（prices_daily / raw_financials を想定）。SQLite は監視・発注ログ保存などの軽量ストレージ用途で併用。
- Paper Trading 実行は本番データと完全分離されるように設計（専用 SQLite パスを使用）。

### Fixed
- .env パーサの実装により、export 付き行、クォート内のエスケープ、インラインコメントなどのケースを正しく扱うよう改善。

### Notes
- 多くのモジュールは「DB を直接操作しない」「外部 API には直接アクセスしない（研究モジュール等）」という設計方針で実装されているため、ユニットテストがしやすい構造になっています。
- AI スコアリング機能は外部 API（OpenAI）を使用するため、OPENAI_API_KEY の設定が必要です。score_news は API が未設定の場合に ValueError を投げます。
- run_monitoring と run_execution は起動時にプロセス優先度を high に設定しようとしますが、権限や OS によっては警告が出てスキップされます。

## [0.1.0] - 2026-04-12

初回リリース — 以下の主要機能を導入

### Added
- 基本的な自動売買フレームワークのコアコンポーネント（ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler 等）の起動フロー（run_execution.py）。
- システム監視用のポーリングループと監視 DB 初期化（run_monitoring.py, monitoring_db 初期化ロジック）。
- ポートフォリオ構築、リスク調整、ポジション決定の純粋関数群（portfolio パッケージ）。
- ファクター計算・研究用途ユーティリティ（research パッケージ: factor_research, feature_exploration）。
- AI を用いたニュースセンチメント集計（ai.news_nlp: OpenAI 経由のバッチ評価ロジック）。
- 環境変数/設定管理（config.Settings と .env 自動ロードロジック）。
- 運用ツール（tools.paper_verification_report）による Paper Trading の検証レポート出力。
- プロセス優先度・CPU affinity ユーティリティ（utils.process_priority）。

### Security
- なし

### Breaking Changes
- なし（初回リリース）

---

変更点やバージョン付けに関する質問や、個々の機能についての詳細なドキュメント化（関数ごとの使用例、入出力仕様、テストケース案など）が必要であれば、対象モジュールを指定してご依頼ください。