# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
バージョニングは package の __version__（src/kabusys/__init__.py の "0.1.0"）に合わせています。

## [Unreleased]

### Added
- 全体
  - 初期リリース相当のコア機能を追加（バージョン 0.1.0 に該当する内容を以下に列挙）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を設定し（utils.process_priority.set_process_priority）、Broker クライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて engine.run_session() を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は実行環境に関わらず本番 sqlite_path を使用。
- 設定/環境変数管理
  - src/kabusys/config.py: 環境変数読み込み・管理モジュールを追加。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パーサーの追加（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
    - Settings クラスを導入し各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境判定、PAPER_FILL_MODE バリデーション等）を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定・重み計算関数（select_candidates, calc_equal_weights, calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター上限適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 株数決定および投下資金スケーリング機構（calc_position_sizes）を追加。単元株（lot）丸め、aggregate cap によるスケールダウン・残差処理を実装。
  - portfolio パッケージで上記をエクスポート。
- 研究（Research）機能
  - research.factor_research: DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）を追加。prices_daily/raw_financials テーブル参照で各種ファクターを算出。
  - research.feature_exploration: 将来リターン算出（calc_forward_returns）、IC（calc_ic）・統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を追加。
  - research パッケージで zscore_normalize 等を含む公開 API を整備。
- AI ニュース/NLP
  - ai.news_nlp: raw_news を OpenAI API（デフォルト gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大20銘柄/回）、文字数・記事数トリム、JSON モード検証、スコアクリッピング（±1.0）、429/ネットワーク/5xx に対する指数バックオフリトライなどの堅牢化を実装。
    - タイムウィンドウ計算ユーティリティ calc_news_window を追加（JST 基準で前日15:00〜当日08:30 の UTC 変換）。
- ツール
  - tools.paper_verification_report: Paper Trading DB（デフォルト data/paper_trading.db）を基に検証レポートを生成する CLI ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を出力する。CLI フラグ --from/--to/--db に対応。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定（Windows/Linux/macOS サポート）と CPU affinity 設定ユーティリティを追加。権限不足や未対応プラットフォームでは警告ログを出してスキップする安全策を実装。

### Changed
- DB の扱い
  - run_execution.py: KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（Settings.paper_sqlite_path）を使用し、本番 DB と完全に分離する挙動を実装。
  - run_monitoring.py: 監視用プロセスは環境に依存せず常に Settings.sqlite_path（本番の monitoring DB）を使用する旨を明確化。
- 設定読み込みの優先順位
  - OS 環境変数 > .env.local > .env の優先順位で自動読み込みを行う（.env.local は .env を上書き）。ただし OS の既存キーは保護される（protected）。

### Fixed
- 環境変数パースの堅牢化
  - .env のクォート文字列内にバックスラッシュエスケープを正しく処理するように改善。クォートなし行のインラインコメント判定は前の文字がスペース/タブの場合にのみコメントと解釈するように調整。
- run_monitoring のポーリング間隔
  - MONITOR_POLL_INTERVAL の値が整数でない、または 1 未満の場合は警告を出してデフォルト（60 秒）へフォールバックするようにして time.sleep の ValueError を回避。
- position_sizing のスケーリング
  - aggregate cap を満たさない場合にスケールダウンして lot_size 単位で残差処理を行うロジックを追加し、再現性（安定した順序）を保つため同一 fractional 残余時は code を二次キーにして順序決定するよう改善。

### Security
- ai.news_nlp: OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で指定する必要があり、未設定時は ValueError を送出して明示的に失敗させるようにした（キー漏洩防止のためログ出力等は行わない前提）。

### Documentation / CLI
- 各モジュールに docstring と使用例を追加。tools.paper_verification_report と ai/news_nlp などはコマンドラインエントリポイントの説明を含むヘルプを提供。

### Notes / Breaking Changes
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用 monitoring DB）を使用します。開発や paper_trading 環境で監視を別 DB に分けたい場合はスクリプトを変更するか、Settings.sqlite_path の環境変数(SQLITE_PATH)を切り替えてください。
- .env の自動読み込みはデフォルトで有効です。テストや CI などで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE の値が不正な場合は起動時に ValueError を送出します（有効値: "instant" | "partial" | "never" | "reject"）。

## [0.1.0] - 2026-04-12
- 初回公開リリース（上記 Added の内容を含む初期機能群をパッケージ化）。

（注）この CHANGELOG は提供されたコードベースを元に推測して作成しています。実際のコミット履歴・変更履歴と差異がある可能性があります。リリース作業時はコミット単位での変更点・作者情報・テスト状況を併せて記載することを推奨します。