CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: KabuSys パッケージを公開。
- 実行エントリ:
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading 専用の SQLite DB に記録することで本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理:
  - config.Settings を実装。環境変数や .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）をサポート。自動ロード無効化用に KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 各種設定プロパティ（DB パス、PID/KILL ファイルパス、閾値、ログレベル、環境名判定、PAPER_FILL_MODE 等）にバリデーションとデフォルト値を実装。
- 監視・可観測性:
  - monitoring モジュールの初期化ヘルパー（init_monitoring_db）および SystemMonitor 起動をサポート。監視は環境に関わらず本番 sqlite_path を使用する旨を明記。
- ポートフォリオ構築:
  - portfolio モジュールを実装（純粋関数群）。
    - portfolio_builder: 候補選定（select_candidates）、等分配・スコア重み（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター上限フィルタ（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算（calc_position_sizes）。lot_size・cost_buffer を考慮したスケーリング、aggregate cap ロジック、risk_based / equal / score 各方式をサポート。
- リサーチ・ファクター計算:
  - research モジュールを実装。
    - factor_research: momentum / volatility / value のファクター計算（DuckDB 接続を受け、prices_daily / raw_financials を参照）。
    - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク変換ユーティリティ。
- AI ニュース NLP:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコア化する処理を実装。バッチサイズ・リトライ・スコアクリッピング・レスポンス検証・部分更新（該当コードのみ置換）を含む堅牢なワークフローを提供。OPENAI_API_KEY が必要（引数から渡すことも可能）。
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）をサポート。
- ユーティリティ:
  - utils.process_priority: Windows / POSIX 差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。権限不足等は警告でスキップするフェイルセーフ設計。
- パッケージ情報:
  - パッケージメタ情報に __version__ = "0.1.0" を設定。

Changed
- DuckDB と SQLite の併用を想定した設計:
  - 実行エンジンは DuckDB（分析用）と SQLite（トランザクション・監視用）の両方を接続して利用。
- .env 読み込みの優先度:
  - OS 環境 > .env.local > .env となるよう自動ロードを実装。OS 環境変数は保護され、.env.local は上書き用に使用される。
- エラーハンドリング:
  - 各所で操作不能・データ欠損時に安全にフォールバックする実装（例: factor 計算でデータ不足の際は None を返す、monitor の check_once 内で例外を捕捉して継続）。

Fixed
- （初回リリースのため特定のバグ修正履歴なし。コード中にデータ欠損や権限不足に対する堅牢化の実装あり。）

Security
- 環境変数の取り扱い:
  - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を提供し、テスト等で外部環境の影響を排除可能。
  - OpenAI API キーは環境変数または明示的引数で渡す必要がある（未設定時は ValueError を送出）。

Notes / Upgrade Notes
- run_monitoring は「環境にかかわらず」settings.sqlite_path（本番用）を使用する設計です。テスト環境や paper_trading で監視を分離したい場合は設定（SQLITE_PATH）を明示的に変更してください。
- run_execution は paper_trading 環境で paper_sqlite_path を使用して本番 DB と分離します。Paper 環境でのデータ参照・集計は data/paper_trading.db（デフォルト）を確認してください。
- PAPER_FILL_MODE の有効値は "instant", "partial", "never", "reject" のいずれかのみ受け付けます。無効な値は起動時に例外となります。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 経由で要求されます。未設定時は ValueError が発生しますので .env を準備してください。
- ai.news_nlp を利用する場合は OpenAI API の利用料金・API 利用制限に注意してください。また、モデルや API レスポンス仕様の変更は将来のリトライ・バリデーションロジックに影響を与える可能性があります。

Acknowledgements
- 本リリースは内部設計文書（PortfolioConstruction.md, StrategyModel.md 等）や実行要件に基づいて実装された純粋関数群・運用スクリプト群を含みます。