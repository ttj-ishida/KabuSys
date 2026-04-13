CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------

- なし（最新の安定リリースは下記参照）。

0.1.0 - 2026-04-13
-----------------

Added
- 基本アーキテクチャと主要機能を実装（初回リリース）。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。起動時にプロセス優先度を "high" に設定。
- 設定管理
  - robust な .env ローダーを実装（.env/.env.local をプロジェクトルートから自動読み込み、OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化に対応。
  - Settings クラスを追加し、各種環境変数（J-Quants、kabuAPI、LINE、DB パス、paper_trading 用設定、監視フラグ、閾値、ログレベル、環境種別判定など）をプロパティ経由で提供。環境変数のバリデーションを実装（例えば KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証）。
- DB 関連
  - sqlite3（monitoring/paper_trading）と DuckDB の接続を想定。init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を追加。
- 実行系コンポーネント（Execution）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの組み立てと起動フローを実装。RiskConfig の初期値例を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナル選出（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: risk_based / equal / score の各配分方式による株数計算（calc_position_sizes）を実装。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、現保有差分計算などをサポート。
- 研究モジュール（research）
  - factor_research: モメンタム、ボラティリティ、バリュー関連ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。DuckDB を使った SQL ベースの実装で prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）、ランク付けユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリで実装。
- AI ニューススコアリング（ai）
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込むワークフローを実装。バッチ処理（最大 20 銘柄/回）、JSON Mode での整形、429/ネットワーク/5xx などに対するリトライ（指数バックオフ）、スコアの ±1.0 クリップ、レスポンス検証などを備える。
  - calc_news_window: ニュース収集ウィンドウ（JST 基準 → UTC）計算ユーティリティを追加。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定（閾値はソース中で定義）を出力。期間指定（--from/--to）と DB パス指定（--db）に対応。
- ユーティリティ
  - utils/process_priority.py: Windows/Linux/macOS を吸収したプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定関数（set_cpu_affinity）を追加。アクセス権限エラー等でスキップする堅牢な実装。

Changed
- なし（初回リリースのため、既存機能の変更はなし）。

Fixed
- 環境変数パーサーの堅牢化: .env の行パースで export 形式、クォート内エスケープ、インラインコメントの扱い、無効行のスキップなどをハンドリング。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出しデフォルト値へフォールバックする処理を追加（run_monitoring のロジック）。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は明示的にエラーを返す（ai/news_nlp.py）。

Notes / Breaking Changes
- run_monitoring はコメントにあるとおり「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」実装になっているため、開発/テスト環境での実行時は DB 書き込み先に注意してください（意図的な分離が必要な場合は Settings や環境変数で調整してください）。
- paper_trading 実行時は run_execution が paper_sqlite_path を使い、データが本番 sqlite と完全に分離される設計です。PAPER_TRADING_SQLITE_PATH でパス上書き可能。

開発者向けメモ
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブル構造に依存するため、テストデータ準備時は該当スキーマを満たしてください。
- calc_position_sizes 等は単元株（lot_size）や cost_buffer の扱いに注意。将来的に銘柄ごとの lot_size を持たせる拡張を想定している箇所あり。

---

（この CHANGELOG はソースコードの記述・コメントから推測して作成しています。実際のリリースノート作成時は変更差分／コミットログを参照して調整してください。）