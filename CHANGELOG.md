# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠します。  
このファイルは、コードベースから推測できる実装内容・振る舞いに基づいて作成しています。

全般的な注記
- 環境変数とデフォルトファイルパスに関する挙動や API クライアントの利用、DB（SQLite / DuckDB）参照などはソースコードから推測しています。  
- 実際のコミット履歴が無いため、機能追加や修正はリリース相当のまとまりとしてまとめています。

## [Unreleased]

### Added
- 監視・実行系の起動スクリプトを整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。監視は常に本番用の sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用し、MockBroker を経由して paper_trading と本番 DB を分離。
- 環境変数 / 設定管理モジュール追加
  - config.py: .env ファイルの自動読み込み（プロジェクトルート検出）を実装。export キーワードやシングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、各種設定（API トークン、DB パス、監視閾値、PID/KILL フラグパス、環境種別など）をプロパティとして取得可能に。
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）や KABUSYS_ENV の有効値チェック（development/paper_trading/live）を追加。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder: 候補選定/スコア降順・タイブレーク、等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に応じた株数計算、lot_size（単元株）を考慮した丸め、aggregate cap によるスケールダウンと残差配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier、bull/neutral/bear）を実装。
- 研究・分析ツール群
  - research.factor_research: DuckDB 接続を受け取り、momemtum / volatility / value ファクターを計算する関数（calc_momentum, calc_volatility, calc_value）を追加。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）やランク関数、ファクター統計サマリー（factor_summary）を追加。外部ライブラリに依存しない純 Python 実装。
  - research パッケージのエクスポートを整備（zscore_normalize を含む）。
- AI ニューススコアリング
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でバッチ処理し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む実装を追加（バッチサイズやトークン肥大対策、最大リトライ、クリッピングなどの安全策を含む）。API キー未指定時はエラーを出す。
- ユーティリティ
  - utils.process_priority: Windows / POSIX（Linux / Darwin / FreeBSD）を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足や未対応 OS では警告をログに出してスキップする。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間指定で検証レポートを出力する CLI を追加。稼働率、注文成功率・送信率、リスク却下数、P95 レイテンシ等を集計して PASS/FAIL を判定する。

### Changed
- DB 利用設計
  - DuckDB を分析用に採用し、各研究関数は DuckDB 接続を受ける（prices_daily / raw_financials テーブルを想定）。実行系は DuckDB と SQLite 両方に接続して使用する。
- 実行時優先度設定
  - run_monitoring/run_execution のいずれも起動直後に set_process_priority("high") を呼んでプロセス優先度を上げるように変更。

### Fixed
- .env パーサの堅牢化
  - クォートやバックスラッシュエスケープ対応、コメント判定の改善、export フォーマットのサポートなどにより .env のパース精度を向上。
- position_sizing の端数配分アルゴリズムの安全弁
  - aggregate cap スケーリング時に lot_size 単位での調整を行い、残余キャッシュで fractional 残差が大きい順に追加配分するロジックを導入。

### Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用する設計。未設定の場合は明示的に ValueError を送出して処理を中断（無制御なキー読み取りを防止）。

---

## [0.1.0] - 2026-04-13

初期公開リリース（ソースコードから推測）

### Added
- パッケージ基本情報
  - kabusys.__init__ に __version__ = "0.1.0" を設定。
- 基本的なアプリケーション構成を実装
  - 実行・監視ランチャー、設定読み込み、ユーティリティ、ポートフォリオ構築、リサーチ、AI ニューススコア、運用ツールなど、取引システムに必要な主要モジュール群を追加。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db を参照して使用）。
- ExecutionEngine 起動に必要なコンポーネントの組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）を起動スクリプトで結合。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

---

注意事項 / 運用メモ
- 監視（run_monitoring）はコメント通り「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」するため、開発・ペーパートレーディング環境で試す場合はデータの混在に注意してください。実行系（run_execution）は is_paper 判定で paper_sqlite_path を使用するため paper_trading は分離されます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージ配布後や特殊な配置では自動ロードがスキップされる場合があります。その際は環境変数を明示的に設定してください。
- OpenAI を利用する機能（ai.news_nlp）を本番で有効化する際は API キーと利用制限・コストに注意してください。ネットワークエラーや 429 の時はリトライを行いますが、過剰なリクエストは避けることを推奨します。

（以上）