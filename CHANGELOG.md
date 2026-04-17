CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

v0.1.0 - 2026-04-17
-------------------

Added
- 全体
  - パッケージ初期リリース相当。モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、ユーティリティ、ツール類、AI ニュース NLP スコアリング等のコア機能を実装。
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - KABUSYS_ENV の値にかかわらず本番用 sqlite_path を使用して監視データを記録する設計になっている点を明示。
    - 停止フラグ (data/stop_requested.flag) による安全停止、プロセス優先度を High に設定する処理、duckdb 接続を併用して初期化を行う。
    - check_once() 実行中の例外を捕捉してログ出力後に次ポーリングへ復帰するフェイルセーフを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に完全分離して記録。
    - 停止フラグによる起動抑止および実行中の停止指示、実行用 PID ファイル管理、スレッドでの engine.run_session() 実行制御を実装。
    - 実行前に監視テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得（DB パス、API トークン、監視閾値、環境判定フラグ等）。
    - .env/.env.local の自動読み込み機構を導入（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
    - .env パーサを堅牢化（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査、各種監視閾値のプロパティ提供。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを実装（コマンドライン実行可能: python -m kabusys.tools.paper_verification_report）。
    - 指定期間／デフォルト期間で system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を出力。
    - P95 計算、日付フィルタリング、DB 存在チェック、SQL の存在しないテーブルを許容するフォールバックを備える。
    - デフォルト閾値（稼働率 99.0% 等）とレポートの整形表示を追加。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選択（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター別時価を計算して上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull=1.0, neutral=0.7, bear=0.3、未知はフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（risk_based / equal / score）を実装。損切り率・リスク許容率・単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケールダウン、cost_buffer を用いた保守的見積り等を備える。

- 実行（Execution）関連
  - run_execution 内で OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てるフローを追加。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）を実装し、初期ポートフォリオ値を broker.get_available_cash() で取得。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを実装（psutil 利用）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する定義、失敗時の安全なフォールバック（警告ログ）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）ファクター計算を実装。DuckDB 接続を受け SQL で高速集計。
    - データ不足のハンドリング（ウィンドウ行数が足りない場合 None を返す等）。
  - research/feature_exploration.py
    - 将来リターン（複数ホライズン）計算、IC（Spearman の ρ）算出、rank（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini 等）でセンチメント解析し ai_scores テーブルに書き込むためのモジュールを追加（設計・定数・エラーハンドリング方針を含む）。
    - ニュース収集ウィンドウ計算（calc_news_window）、API キー解決やバッチ処理の方針、リトライ/バックオフ、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ等を実装予定。score_news の一部実装が含まれる（ファイル末尾はトランケートあり）。

Changed
- .env の自動読み込み順序を明確化（OS 環境 > .env.local > .env）。既存 OS 環境変数は保護され、.env.local は既存 OS 環境を上書きしないが通常の .env は未設定キーのみ設定する挙動。

Fixed
- init_monitoring_db は起動時に監視テーブルが存在しない場合に作成する処理を呼び出すようにし、run_execution 起動時にも呼んで冪等性を確保。

Potential breaking changes / 注意点
- run_monitoring は「KABUSYS_ENV の値にかかわらず本番 sqlite_path を使用する」仕様になっているため、開発環境で監視を起動すると本番の monitoring.db に書き込む可能性があります。開発時は Settings の環境変数（SQLITE_PATH 等）や実行スクリプトの配置に注意してください。
- ai/news_nlp.py の score_news 実装は未完（ファイル末尾が切れているためそのままでは実行できない箇所があります）。本機能を使用する場合は続きの実装が必要です。

Notes
- 各モジュールは外部 API（発注 API 等）に直接アクセスしない設計とする部分（research / portfolio モジュール等）があり、安全にローカル検証が可能な構成を目指しています。
- DuckDB を分析用の高速集計に使用し、SQLite をランタイムのトランザクション / ログ保管に使用するハイブリッド構成を採用しています。

今後の予定（例）
- ai/news_nlp.score_news の完全実装および E2E テストの追加。
- run_monitoring の開発用挙動（テスト用 DB の利用など）を選択可能にするオプション追加。
- より詳細なドキュメント（API ドキュメント、運用手順、各モジュールのユースケース例）の整備。

--- 

この CHANGELOG はコードからの導出に基づく推測を含みます。実際のコミット履歴や意図と差異がある場合がありますので、必要に応じて調整してください。