CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 基本メタ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止指示はプロジェクトルート/data/stop_requested.flag ファイルで検知。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を利用）。
    - 監視テーブルの初期化（init_monitoring_db）および DuckDB 接続を行う。
    - 例外耐性: monitor.check_once() の例外は捕捉して次回ポーリングへ継続。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する旨の挙動。

  - run_execution.py を追加。ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成。
    - OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を別スレッドで起動。
    - 停止指示は data/stop_requested.flag で検知し engine.stop() を呼び出す。
    - 起動時にプロセス優先度を設定。実行 PID ファイル path をサポート。

- 設定管理
  - config.py を導入。.env/.env.local 自動読み込み（プロジェクトルートに .git または pyproject.toml がある場合）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - export KEY=val 形式やクォート・コメントを考慮した堅牢な .env パーサを実装。
    - Settings クラスを提供し、各種設定値（パス、閾値、API トークン、環境判定など）をプロパティ経由で取得。値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証等）を実装。
    - settings = Settings() のインスタンスをモジュールレベルでエクスポート。

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用の検証レポート生成スクリプト。
    - CLI (--from, --to, --db) を提供。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - system_status / trade_logs / risk_logs テーブル等から稼働率、注文成功率（Fill/Send）、リスク却下数、レイテンシ（平均/最大/P95）を算出し、PASS/FAIL 判定を出力。
    - P95 計算、SQL クエリ断面ごとの例外ハンドリング（SQLite のテーブル未存在時のフォールバック）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定・等重・スコア重み化（score が全て 0 の場合は等重にフォールバック）。
  - portfolio.position_sizing: ポジションサイズ計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、コストバッファ対応。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知のレジームは警告ログを出してフォールバック。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB を使ったファクター計算を実装（momenta, volatility, value）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率。
    - calc_value: raw_financials と株価から PER / ROE を計算（target_date 以前の最新財務を利用）。
  - research.feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクターの統計サマリ、ランキング関数を実装（外部ライブラリ非依存）。
  - research.__init__ で主要 API をエクスポート。

- AI / ニュース NLP（ニュースセンチメント）
  - ai/news_nlp.py を追加（OpenAI を用いたニュースのセンチメントスコアリング）。
    - ニュース収集ウィンドウの計算（JST → UTC の変換）を実装（calc_news_window）。
    - スコア生成関数 score_news の骨格を実装（OpenAI API キー要、バッチ送信、リトライ戦略、レスポンス検証、スコアクリップ等を記載）。
    - 注意: 実装は API 呼び出し・レスポンス処理・DB 書き込みを含む設計になっているが、ソース末尾が断片的に切れている（score_news の続きが未表示の可能性がある）ため、実運用前に完全な関数実装の確認が必要。

- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。権限不足や未サポート環境では警告ログを出して安全にフォールバック。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known Issues / Notes
- ai/news_nlp.score_news のソースが途中で切れている（表示されているコード末尾が不完全）ため、OpenAI API 周りの完全な動作確認および DB 書込ロジックの最終化が必要です。
- position_sizing.calc_position_sizes の price フォールバック（価格欠損時の扱い）について TODO コメントあり。前日終値や取得原価などのフォールバック実装は未実施。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」仕様のため、検証環境での取り扱いに注意（意図的な設計だが運用上の注意を要します）。

Notes for operators / developers
- 環境変数関連
  - .env 自動読み込みはデフォルトで有効。テストや特殊な状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
  - 監視のポーリング間隔は MONITOR_POLL_INTERVAL で制御（秒、1 以上、無効値はデフォルト 60 秒にフォールバック）。
  - Paper Trading 用の DB パスは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。
  - OpenAI API を利用する機能は OPENAI_API_KEY が必要（score_news は未設定時に ValueError を投げる実装）。
  - PAPER_FILL_MODE は instant/partial/never/reject のいずれかを指定（不正値は ValueError）。

- 実行
  - 監視: python -m kabusys.run_monitoring（または該当スクリプトの直接実行）。
  - 実行エンジン: python -m kabusys.run_execution（paper_trading 環境では別 DB を使用）。

References
- ソースファイル一覧（主な追加/実装箇所）
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_execution.py
  - src/kabusys/config.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/portfolio/*.py
  - src/kabusys/research/*.py
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/utils/process_priority.py

（初回リリース）