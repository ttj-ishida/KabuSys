CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  
バージョン番号は semver に従います。

[Unreleased]
-------------
（未リリースの変更はここに記載）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本アプリケーション初版を追加。
  - パッケージ情報: kabusys v0.1.0
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モード時は MockBrokerClient と専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
- 設定管理
  - config.py: 環境変数読み込みユーティリティを実装（.env / .env.local の自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサ: export 表記、クォート文字列とバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - Settings クラスを導入し、各種設定（DBパス、APIトークン、監視閾値、env/log レベル等）をプロパティ経由で提供。
  - 設定のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 監視・運用系
  - monitoring_db 初期化呼び出しを run_* スクリプトに追加（監視テーブルの存在保証）。
  - PID/KILL フラグ関連設定を Settings から提供（pid_file_path, kill_flag_path, kill_flag_clear_on_start）。
- 実行系（Execution）
  - ExecutionEngine 組み立てロジックを run_execution に追加。OrderRepository / OrderManager / RiskManager / Reconciler を統合してセッション実行。
  - RiskConfig に初期 portfolio 値を broker.get_available_cash() から取得する初期化処理を組み込み。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額・スコア加重（calc_equal_weights, calc_score_weights）を実装。スコア全0 の場合に等分配へフォールバック。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）を実装。lot_size 単位で丸め、集計上限（aggregate cap）を超える場合はスケールダウンして残差を lot 単位で再配分する安全ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームは警告のうえ 1.0 でフォールバック。
- 研究・ファクター算出（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe）を DuckDB SQL で実装。データ不足時の None ハンドリングあり。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず純 Python + DuckDB。
  - research パッケージのエクスポートを整備（zscore_normalize を含む）。
- ニュース NLP（OpenAI 統合）
  - ai.news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、トークン肥大対策（記事数・文字数上限）、JSON mode 出力の厳格検証、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク/5xx 等に対する指数バックオフリトライを実装（上限あり）。
    - OpenAI API キー未設定時は ValueError を送出。
- 運用ユーティリティ
  - utils.process_priority: プロセス優先度設定（Windows/Linux/macOS 等対応）と CPU affinity 設定を実装。権限不足や未対応 OS の場合は警告してスキップする堅牢設計。
- ツール類
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db。P95 計算、閾値定義、期間フィルタ対応あり。
- パッケージ初期化
  - kabusys.__init__ にバージョンと主要エクスポートを追加。

Changed
- N/A（初回リリースのため既存変更はなし）

Fixed
- 設定・入力検証を強化
  - PAPER_FILL_MODE の無効値チェックを追加し、不正な値は ValueError を発生させるように。
  - KABUSYS_ENV / LOG_LEVEL の検証を追加。無効値で ValueError を発生。
  - MONITOR_POLL_INTERVAL のパースで負値や 0 を無効としてデフォルトにフォールバックし、無効値時に warning を出力。
- .env ローダーのファイル読み込み失敗時に warnings.warn を使って警告を出すように。

Security
- ai.news_nlp: OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で指定する必要がある。未設定の場合はエラーで処理を停止し、キーの誤使用を避ける設計。
- .env 自動ロード機構は OS 環境変数を保護（protected）し、.env.local の override にも OS 環境を上書きしないよう配慮。

Known issues / Notes / TODO
- portfolio.position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価などのフォールバック価格導入を検討中（コメントに TODO）。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map への拡張を予定。
- ai.news_nlp:
  - ロジックは外部 API に依存するため、API の変更に伴う調整が必要になる可能性がある。レスポンスバリデーションを厳格に行っているが、モデル出力の変化は注意点。
- run_monitoring:
  - 監視は常に settings.sqlite_path（本番 DB）を参照する仕様。テスト環境から監視データを分離したい場合は運用手順で代替する必要あり。
- DuckDB クエリは prices_daily / raw_financials 等のスキーマに依存するため、データ投入時のスキーマ整合性に注意。

Upgrade instructions
- 既存環境からの移行は該当しません（初回リリース）。
- 実運用での注意:
  - OpenAI 連携機能を使う場合は OPENAI_API_KEY を設定してください。
  - paper_trading モードを使用する場合は PAPER_TRADING_SQLITE_PATH を適切に設定して、本番データと分離してください。
  - 環境変数の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

References
- 設定例と .env 書式については config.py の実装を参照してください。
- 各アルゴリズムの詳細はソース内コメント（PortfolioConstruction.md / StrategyModel.md 相当の参照）を参照ください。

--- 
（この CHANGELOG は提供されたソースコードから推測して作成しています。リリース文書として正式に採用する前に、実際の運用・設計方針やリポジトリの履歴と照合してください。）