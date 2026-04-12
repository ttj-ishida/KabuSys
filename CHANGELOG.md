CHANGELOG
=========

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」規約に準拠します。
バージョン番号はセマンティックバージョニングに準拠します。

Unreleased
----------

- 監視・実行・研究・ポートフォリオ・NLP 等の各モジュールについて、堅牢性・ログ・入力検証を強化。
- config の .env 自動読み込みロジックに対する微調整（プロジェクトルート探索の堅牢化、.env/.env.local の読み込み順制御）。
- 細かいログ出力の追加・改善や例外ハンドリングの強化（monitoring/ai/position sizing 等）。

[0.1.0] - 2026-04-12
--------------------

Added
- 基本リリース（初期実装）。
- 起動スクリプト:
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用する旨をサポート。
    - ブローカークライアントのファクトリ利用（BrokerClientFactory）を想定し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0/負値はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（誤運用を防ぐ設計上の挙動として明記）。
- 設定管理:
  - config.py
    - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - export 形式やクォート付き値、インラインコメントの取り扱いに対応する堅牢なパーサ (_parse_env_line) を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
    - Settings クラスを実装し、各種環境変数（DB パス、API トークン、監視閾値、PID/KILL ファイルパス、環境モードなど）をプロパティとして提供。入力値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
- ポートフォリオ構築:
  - portfolio.portfolio_builder
    - シグナル選定 (select_candidates)、等配分・スコア加重 (calc_equal_weights / calc_score_weights) を提供。
    - スコアが全て 0 の場合の警告とフォールバック挙動を実装。
  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄を除外可能、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" をサポート、未知のレジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - 各銘柄の発注株数計算 calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer 考慮、単元配分の切り上げロジックなど）。
- 研究（research）:
  - research.factor_research
    - モメンタム / ボラティリティ / バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB 接続を受けて実行する実装を追加。200日 MA・ATR・複数ホライズン等を考慮。
  - research.feature_exploration
    - 将来リターン計算 calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary を提供。外部ライブラリに依存しない純標準ライブラリ実装。
  - research.__init__
    - 主要関数と zscore_normalize（data.stats 由来）をエクスポート。
- AI / ニュース NLP:
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込むフレームワークを実装。
    - バッチ処理（1バッチ最大 20 銘柄）、トークン肥大対策（最大記事数・最大文字数トリム）、JSON Mode 期待のシステムプロンプト、429/5xx/ネットワーク等への指数バックオフリトライ等を想定した設計。
    - API キー解決・ウィンドウ計算（JST→UTC 変換）やレスポンス検証、スコア ±1.0 クリップ、部分失敗時の既存スコア保護（DELETE→INSERT の対象を限定）といったフェイルセーフ設計を含む。
- ユーティリティ:
  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX（Linux/Darwin/FreeBSD）差分を吸収し、権限不足等の失敗を警告ログでハンドル。
- 管理ツール:
  - tools.paper_verification_report
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。欠損テーブルに対する耐性を追加（OperationalError を捕捉して N/A を出力）。

Changed
- logging の初期化を各起動スクリプト内で行い、INFO レベルをデフォルトに設定。
- DB 接続取り扱い: monitoring 用 DB 初期化を init_monitoring_db 呼び出しで冪等に保証。

Fixed
- .env パーシングにおけるクォート内エスケープ、インラインコメント処理、export プレフィックス対応など、実運用で起きうるケースを修正・サポート。
- スレッド／ループ処理での例外ハンドリング強化（monitor.poll ループ内で check_once が例外を投げてもループ継続）。

Notes / Breaking changes / Warnings
- run_monitoring は KABUSYS_ENV にかかわらず monitoring 用に Settings.sqlite_path（"本番" 相当）を使用します。テスト目的で monitoring を起動する場合は sqlite_path を明示的に切り替えるか、設定を調整してください（paper_trading 用 DB は run_execution が使用する）。
- MONITOR_POLL_INTERVAL に 0 や負数、非数を設定するとデフォルト（60 秒）にフォールバックし警告が出ます。
- PAPER_FILL_MODE の値は厳格に検証され、無効値は ValueError を送出します。環境変数設定時は注意してください。

Security
- OpenAI API キー等の機密情報は Settings を通じて環境変数から取得します。.env の自動ロードはデフォルトで有効ですが、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。公開環境では .env の管理に注意してください。

Acknowledgements
- 初期実装では DuckDB と sqlite3 をデータ処理基盤に採用し、psutil によりプロセス制御（優先度 / CPU affinity）を行っています。

-- end --