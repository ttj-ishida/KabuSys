CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の方針に準拠します。
このファイルはコードから推測できる変更点・機能追加・修正点をまとめた推定の変更履歴です。

フォーマット:
- Unreleased（次期リリースに向けた未リリースの変更）
- 各リリースは 変更のカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに記載

Unreleased
----------
(開発中 / 次期リリース候補)

Added
- AI ニューススコアリングモジュールを追加（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコア算出を実装する設計を導入。
  - バッチ処理（最大20銘柄/コール）、記事数/文字数トリム、スコアの ±1.0 クリッピング、JSON レスポンス検証、リトライ（指数バックオフ）戦略をサポートする仕様を追加。
  - ニュース収集ウィンドウの計算関数（calc_news_window）を追加し、JST/UTC の変換ロジックを明確化。
  - ※score_news の処理は部分実装（ファイル断片により途中で切れているため、未完の箇所あり）。将来的な完成が必要。

- ファクター・リサーチ機能を追加（kabusys.research.factor_research）
  - Momentum / Volatility / Value ファクター計算関数を導入（calc_momentum, calc_volatility, calc_value）。
  - DuckDB 接続を受け、prices_daily / raw_financials テーブルからファクターを算出する方式。
  - 計算のための窓幅・スキャン幅等の定数を定義し、空データや不十分な窓長の扱いを明示。

- 研究用ユーティリティを追加（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。
  - 外部依存（pandas 等）を使わない純粋 Python 実装。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - ポジションサイズ計算（calc_position_sizes）を実装（リスクベース・等分配・スコア加重に対応、単元株丸め、aggregate cap スケーリング、コストバッファ対応）。

- 実行系 / 監視系起動スクリプトを提供
  - run_execution.py: ExecutionEngine 起動スクリプト。paper_trading 環境時に専用 DB（data/paper_trading.db）を使用する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検出で優雅に終了。

- Paper Trading 向け検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を行う CLI ツールを追加。
  - デフォルトの閾値（稼働率 99%, 成功率 90% 等）を定義。--from/--to/--db オプションをサポート。

- 設定 / 環境読み込みの強化（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護する protected オプションを実装。
  - 複雑な .env 行（export プレフィックス、クォート・エスケープ、インラインコメント）の安定したパースを実装。
  - 各種設定プロパティを Settings クラスで提供（DB パス、paper_trading 用パス、監視閾値、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows / POSIX 差分を吸収し、失敗時は警告でスキップするフォールバックを実装。

Changed
- run_execution/run_monitoring の起動シーケンスを改善
  - 起動直後にプロセス優先度を設定するよう順序を変更（set_process_priority を最初に実行）。
  - 監視用 DB 初期化（init_monitoring_db）を冪等に実行することでテーブル不在時の安全性を確保。
  - ExecutionEngine は paper_trading モードでは broker を Mock にし、本番 DB とは完全分離される仕様を明示。

Fixed
- 環境変数の不正値ハンドリングを強化
  - MONITOR_POLL_INTERVAL が 0 以下や非数の場合にデフォルト値へフォールバックする処理を追加。
  - PAPER_FILL_MODE の受け入れ値検証を追加し、不正値時に明確な例外メッセージを出力。

Security
- 環境変数の読み込みにおいて OS 既存値を上書かない既定挙動を採用し、誤った自動上書きによるリスクを低減（.env.local では上書き可だが protected により OS 値は保護）。

0.1.0 - 2026-04-16
------------------
Initial release — 基本機能の実装

Added
- パッケージ基本情報
  - パッケージバージョン: 0.1.0（kabusys.__init__.__version__ にて設定）
  - パッケージ構成のエクスポート（__all__）に基本モジュール群を追加。

- コア機能
  - Execution / Order 管理のためのスケルトン（ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の呼び出し・組み立てロジックを run_execution に実装）。
  - モニタリング基盤の初期化ユーティリティ（monitoring_db.init_monitoring_db を利用する形で run_monitoring/run_execution の起動時に DB 検査）。
  - DuckDB と SQLite の併用を明示（duckdb_path / sqlite_path / paper_sqlite_path の設定と接続）。

- portfolio, research, tools, utils の各モジュールの初期実装
  - ポートフォリオ構成、ポジションサイジング、セクター制限、レジーム係数。
  - ファクター計算（Momentum / Volatility / Value）およびリサーチ用ユーティリティ（forward returns, IC 等）。
  - process_priority ユーティリティ。
  - Paper Trading 検証レポートツール。

Changed
- 初期設計方針ドキュメントの参照（コード内 docstring に PortfolioConstruction.md / StrategyModel.md 等の参照を記載）。
- DuckDB を primary analytics DB として利用する設計を採用（prices_daily / raw_financials を想定）。

Fixed
- run_*/tools の CLI /エラー処理に冗長な例外キャッチとログ出力を追加して堅牢性を向上。

Known issues / TODO
- AI ニューススコアリング（kabusys.ai.news_nlp）の score_news 関数実装がファイル終端で途中切れになっており、完全実装が必要（OpenAI 呼び出し結果の集約・DB 書込部分など）。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）や lot_size を銘柄ごとに扱う拡張はコメントで TODO 記載。将来的な改善候補。
- calc_regime_multiplier は未知レジームでフォールバックする実装だが、本来のレジーム識別パイプラインとの接続テストが必要。
- DuckDB executemany の仕様に注意（空 params は失敗するため呼び出し前に検査）。

注記
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や意図と差異がある可能性があります。必要であれば、リリース日・コミットハッシュ・担当者情報を追記します。