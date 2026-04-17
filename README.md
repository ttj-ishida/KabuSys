# KabuSys (README)

以下はこのコードベース（KabuSys）の日本語ドキュメントです。プロジェクトの目的、主な機能、セットアップ手順、実行方法、ディレクトリ構成をまとめています。

概要
- KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。
- 注文発行・リコンシリエーション・リスク管理・監視（システム／注文／ドローダウン監視）・ポートフォリオ構築・ファクター算出・ニュースNLP（OpenAI）などの機能を含みます。
- モジュールは実運用（live）・紙取引（paper_trading）・開発（development）環境を意識した設計になっています。

主な機能
- ExecutionEngine（注文発行 / リスク管理 / リコンシリエーション）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター調整、レジーム乗数）
- 研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースセンチメント: OpenAI を用いた ai_scores の生成、レジーム判定）
- ツール類
  - paper_trading 検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード
- DB 層
  - DuckDB：市場データやファクター計算等の高速集計用
  - SQLite：監視ログ（monitoring.db）／紙取引ログ（paper_trading.db）など永続化用

前提条件（主な外部パッケージ）
- Python 3.9+（型ヒントで | を使用しているため）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- その他：sqlite3 は標準付属

セットアップ手順（ローカル）
1. リポジトリをクローン、プロジェクトルートに移動
   - 例: git clone <repo> && cd <repo>
2. 仮想環境作成／有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際の requirements.txt があればそれを使ってください）
4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意するか、環境変数を直接設定します。
   - 自動的に .env / .env.local が読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

重要な環境変数（主要）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants 関連トークン
- KABU_API_PASSWORD: （必須）kabu ステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）を使う場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: 紙取引用 SQLite（paper_trading 環境時に使用。デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: 紙取引の約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data 以下）

簡単な使い方（実行コマンド例）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使って監視テーブルを初期化します。
  - 停止は data/stop_requested.flag を作るか Ctrl+C（KeyboardInterrupt）。
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）に記録されます（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。停止は同ファイルを作成するか ExecutionEngine 側で kill flag を検知して停止します。
  - 実行時、PID ファイル（data/execution.pid 等）を生成します。
- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き、ポジションや最近のログ、最新システム状況を表示します。
- 紙取引検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の上書き）
  - 紙取引 DB（例: data/paper_trading.db）から稼働率、注文成功率、レイテンシなどを集計して判定を出します。

停止方法（運用上の仕組み）
- ExecutionEngine を外部から停止する手段:
  - KillSwitch により data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます（設定されたフラグパスを使用）。
  - run_monitoring / run_execution は data/stop_requested.flag の存在でループを抜けるようになっています（運用側でこの flag を作成することで安全停止）。
- kill.flag は既に存在する場合は上書きしない（冪等）。clear() を呼ぶことで削除できます（ExecutionEngine 起動時のクリーンアップにも使用）。

データベース & マイグレーション
- Monitoring 用 SQLite（デフォルト data/monitoring.db）
  - init_monitoring_db(conn) が冪等的にテーブル・インデックスを作成。既存 DB に対して必要な列追加（ALTER）を行う処理も含んでいます。
  - テーブル例: system_status, trade_logs（latency_ms を含むようにマイグレーションあり）, positions, risk_logs, dashboard
- Paper trading 用 SQLite（paper_trading 環境時に使用）
  - 本番 DB と完全に分離して記録します（デフォルト: data/paper_trading.db）
- DuckDB（デフォルト data/kabusys.duckdb）
  - 市場データ（prices_daily など）、raw_financials、raw_news、ai_scores、market_regime のクエリ／集計に使用

開発・テストのヒント
- Settings モジュールは .env / .env.local の自動ロードを行います（CWD に依存せずプロジェクトルートを .git または pyproject.toml で検出）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分（news_nlp、regime_detector）は再試行・フォールバック処理を備えています。テスト時は _call_openai_api をモックしてください。
- MonitoringEngine.run_once() や個別 Monitor クラスはユニットテストしやすいよう設計されています（依存を注入可能）。
- ローカルで DB 初期化を行いたい場合は run_monitoring/run_execution を一度起動すると init_monitoring_db が実行されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 永続層（初期化・CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・保有数監視
    - kill_switch.py — kill.flag 書き込み / 評価
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor をまとめる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他 broker_factory, execution_engine, order_repository 等が想定される）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - tools/
    - __init__.py
    - paper_verification_report.py — 紙取引検証レポート
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity

追加メモ
- paper_trading モードでは紙取引専用 DB に記録されるため、本番環境の注文や資金に影響を与えません。デフォルトでは PAPER_FILL_MODE=instant（即時約定）になりますが、partial/never/reject などを指定できます。
- AI（OpenAI）を利用する機能は API キーが必須です。ネットワークや API エラー時は安全側のフォールバックが入りますが、キーを用意してください。
- 運用ではログレベルや環境（KABUSYS_ENV）を適切に設定し、監視アラート（LINE）や KillSwitch の設定を行ってください。

以上。必要ならば README に入れる具体的な .env.example のテンプレートや、requirements.txt、デプロイスクリプト例を追記できます。どの情報を追加しますか？