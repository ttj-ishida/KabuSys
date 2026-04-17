KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。Signal → Execution の実行ロジック、監視/アラート、ポートフォリオ構築、リサーチ/ファクター計算、AI によるニューススコアリングなど、実運用を意識したコンポーネントが含まれます。

主な特徴
--------
- ExecutionEngine（発注・状態管理・リコンシリエーション）
- Monitoring（システム状態・滞留注文・リスク監視、LINE通知、ストリームリットダッシュボード）
- Portfolio construction（候補選定、重み計算、ポジションサイズ算出、セクター制約）
- Research（ファクター計算、将来リターン、IC、統計サマリー）
- AI モジュール（ニュースセンチメント・市場レジーム判定） — OpenAI API を利用
- Paper trading モード（本番 DB と分離された専用 SQLite に記録）
- DuckDB を使った時系列/ファクタ計算、SQLite を使った監視ログ永続化

動作対象
--------
- Python 3.10+
- プラットフォーム: Linux / macOS / Windows（psutil に依存した優先度設定は OS により挙動が異なります）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - その他テスト／開発に必要なパッケージは適宜追加してください。

4. 環境変数 / .env
   - Settings モジュールはプロジェクトルートの .env および .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
   - 代表的な環境変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（実行制御に使用）
   - .env.example を参照して .env を用意してください（リポジトリに同梱がない場合は README に従って設定）。

基本的な使い方
--------------

1. 監視ループ（Monitoring）
   - 目的: SystemMonitor / TradeMonitor / RiskMonitor を定期実行して監視ログやリスクイベントを永続化し、必要に応じてアラート / kill.flag を発行します。
   - 実行:
     - python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
   - 注意:
     - run_monitoring はプロジェクトの data/stop_requested.flag を確認して終了します。停止したい場合はそのファイルを作成してください。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB の状態を見たいケースを想定）。

2. 実行エンジン（Execution）
   - 目的: ブローカークライアントを介した発注、リスク管理、リコンシリエーション等を行う主要プロセス。
   - 本番と paper_trading の振る舞い
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（モック）を使用し、DB は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録されます。本番と完全に分離されます。
   - 実行:
     - python -m kabusys.run_execution
     - 既に data/stop_requested.flag が存在する場合は起動せず終了します。
     - 実行中は data/execution.pid に PID を書きます。停止シグナルは data/stop_requested.flag の作成または kill.flag によるものがあります（KillSwitch が kill.flag を書きます）。

3. Paper Trading 検証レポート（ツール）
   - 目的: paper_trading DB から稼働率・注文成功率・レイテンシ等の指標を集計してレポートを出力します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を直接指定する: --db path/to/paper_trading.db
   - 判定基準（デフォルト閾値）
     - 稼働率 >= 99%
     - 注文成功率（fill rate） >= 90%
     - 送信率 >= 95%
     - P95 レイテンシ <= 200 ms

4. ストリームリット監視ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、ダッシュボード表示を行います。

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY）。key は Settings で参照されるか、各関数に引数で渡せます。
   - 主な公開 API:
     - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を基に銘柄別センチメントを ai_scores テーブルへ書き込む
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ書き込む
   - 注意: API 呼び出しはレート制限や一時エラーに対してリトライ処理を行いますが、失敗時は安全にフォールバックします（例: macro_sentiment = 0.0）。

プロセス制御 / フラグ類
---------------------
- data/stop_requested.flag
  - run_monitoring / run_execution がループ中に存在を検査。作成するとループを終了します（停止要求）。
- data/kill.flag
  - KillSwitch が書き込む flag。ExecutionEngine に対する停止シグナル用途。存在するかを Execution 起動時に Settings.kill_flag_clear_on_start でクリア動作を制御できます。
- data/execution.pid
  - 実行エンジンの PID を記録。SystemMonitor はこの PID を確認してプロセスが生きているかを判定します。

構成ディレクトリ（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py — Monitoring ポーリングループの起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ / 主要モジュール
- ai/
  - news_nlp.py — ニュース記事を OpenAI でセンチメント化して ai_scores へ書き込む
  - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite を使った永続化層（schema 初期化含む）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス検査
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE による通知（push API）
  - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once / 永続 run）
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 発注フローの外向き API（状態管理、重複チェック等）
  - reconciler.py — 起動時の注文・ポジション突合（リコンシリエーション）
  - （その他: broker_factory, execution_engine, order_repository などが存在）
- portfolio/
  - portfolio_builder.py — 候補選定・等重/スコア重み
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

重要な挙動・設計方針（抜粋）
--------------------------
- 設定は Settings クラスを通して環境変数から取得。自動で .env / .env.local をロードする（プロジェクトルートを .git / pyproject.toml で探索）。
- Paper trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出し（OpenAI）は失敗時フォールバックやエクスポネンシャルバックオフを実装。API レスポンスは厳密 JSON を期待しつつパース頑健化している。
- Monitoring は DB スキーマの初期化（init_monitoring_db）と軽量な永続化層（MonitoringDB）を提供。
- position_sizing 等の計算ロジックは純粋関数として実装され DB 参照を持たないためユニットテストしやすい。

よく使うコマンド例
------------------
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（Paper Trading）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

運用上の注意
------------
- システム監視は本番の監視 DB に書き込みます。テスト実行時は PAPER_TRADING_SQLITE_PATH や KABUSYS_ENV を活用して DB を分離してください。
- OpenAI キーやブローカー API 情報は秘匿情報です。 .env を .gitignore に入れて管理してください。
- process_priority の設定は psutil の権限に依存します。権限不足で設定できない場合は警告ログになります（処理は継続します）。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等に設計されています。既存テーブルへの安全なカラム追加処理を含みます。

ライセンス / 貢献
-----------------
- 本 README はコードベースからの抜粋説明です。実際に運用する際はテスト・コードレビューを行ってください。
- 貢献やバグ報告は Pull Request / Issue で受け付けてください（詳細な貢献ガイドはリポジトリに合わせて追加してください）。

---

この README はリポジトリ内の主要な機能と実行手順の概要を示したものです。詳細な設計や API 仕様は該当ソース（各モジュールの docstring）を参照してください。必要であれば、運用ガイドや .env.example のテンプレートを別途作成できます。