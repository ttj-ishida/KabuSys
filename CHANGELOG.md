CHANGELOG
=========

全ての重要な変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-13

### Added
- 初回リリース。KabuSys 自動売買フレームワークのコア機能を追加。
- 実行エントリ／プロセス管理
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境変数 KABUSYS_ENV によって paper_trading モードが切り替わり、paper_trading 時は専用の SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と完全に分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照する。
  - 両スクリプト共にプロセス優先度を最初に "high" に設定する機能を組み込み（utils.process_priority.set_process_priority）。

- 設定管理・環境変数
  - Settings クラスを追加し、環境変数（.env/.env.local 自動読み込みを含む）から設定値を提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export プレフィックス対応、クォート内バックスラッシュエスケープ、インラインコメントの取り扱いなどを考慮）。
  - 設定のバリデーションを導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の許容値検証）。
  - 各種パス設定（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）をプロパティとして提供。

- データベース初期化
  - monitoring 用 DB 初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）を run スクリプトで呼び出し、監視テーブルの冪等な作成を保証。

- Execution コンポーネント
  - BrokerClientFactory によるブローカークライアント生成（本番／モックの切替）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと実行フローを実装。RiskManager にはデフォルトの RiskConfig を設定し、初期ポートフォリオ値は broker.get_available_cash() を参照する。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア全0時は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier)。unknown セクターの扱い、レジームマップ（bull/neutral/bear）を実装。
  - portfolio.position_sizing: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の配分方式、単元株丸め（lot_size）、aggregate cap によるスケーリング、cost_buffer を使った保守的見積り、各種リスクパラメータを実装。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。価格や財務データを参照してモメンタム、ATR、平均売買代金、PER/ROE 等を算出。ウィンドウ不足時の None 扱いなどを考慮。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ランク変換 (rank)、ファクターの統計サマリー (factor_summary) を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- ニュース NLP（OpenAI 統合）
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）でニュースセンチメントを算出し、ai_scores テーブルへ書き込む機能を追加。
  - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム（最大 10 記事・3000 文字/銘柄）、JSON モードのレスポンス検証、スコアを ±1.0 にクリップ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）等の耐障害設計を実装。
  - OpenAI API キーの解決（引数 or 環境変数 OPENAI_API_KEY）、未設定時は ValueError。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。コマンドライン引数で期間指定可能（--from / --to / --db）。監視・注文・リスク・レイテンシ指標を集計して PASS/FAIL 判定（閾値はスクリプト内定義）。P95 計算や欠損ハンドリングを実装。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX（Linux, Darwin, FreeBSD）向けに差分を吸収し、権限不足等は警告ログでスキップする。

- パッケージ情報
  - パッケージの __version__ を 0.1.0 に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Breaking changes / 注意点
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、配布後の実行環境では自動ロードがスキップされる場合があります。必要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して挙動を制御してください。
- PAPER_FILL_MODE など設定値は厳密に検証され、不正値は ValueError を投げます。環境変数は .env.example を参照して正しく設定してください。
- run_monitoring は監視用 DB として常に settings.sqlite_path を使用します（環境に依らず本番の監視 DB に書き込む設計）。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番と分離します。Paper Trading の検証は tools.paper_verification_report を利用してください。
- OpenAI を用いる機能は API キーが必須です。API コール時のエラーは基本的にロギングの上でフェイルセーフ（部分的な失敗を許容）となる設計です。
- DuckDB / SQLite の接続は利用後に確実に close されます。DuckDB バージョン依存の制約（executemany のパラメータ空チェック等）に注意しています。

今後の予定（例）
- 戦略モデル・シグナル生成パイプラインの追加実装
- ブローカークライアントのリアル/モック共通 API の拡充
- テストカバレッジの強化と CI パイプライン整備

（以上）