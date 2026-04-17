# KabuSys — README

以下はこのコードベース（KabuSys）の README です。日本語でプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

概要
- KabuSys は日本株自動売買システムのコアライブラリ群です。
- 主要機能は「注文実行（ExecutionEngine）」「監視（Monitoring）」「ポートフォリオ構築」「研究用ファクター計算」「ニュース NLP を用いた AI スコアリング」など。
- DuckDB を用いた時系列データ処理、SQLite を用いた監視・発注ログ保持、OpenAI API によるニュースセンチメント評価などを含みます。
- 開発・Paper Trading（模擬）・本番（live）を想定した設定管理を持ち、環境による DB 分離や挙動切替が組み込まれています。

主な機能一覧
- Execution
  - 発注の生成・管理（OrderManager）
  - Broker クライアントの抽象化と Factory（本番 / モックの切替）
  - 再起動時のリコンシリエーション（Reconciler）
  - 発注ログ・ポジション永続化（OrderRepository 等、OrderRecord）
- Monitoring
  - システムリソース監視（CPU/MEM/DISK）、プロセス生存チェック（SystemMonitor）
  - 注文の滞留チェック・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - アラート送信（LINE push：AlertManager）
  - Kill Switch（閾値超過時に停止フラグ file を書き込み、Execution を停止）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定、等金額/スコア重み、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数
- Research（研究用）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）、統計サマリー
- AI
  - ニュースのセンチメント評価（OpenAI を利用）：kabusys.ai.news_nlp
  - 市場レジーム判定（ma200 + マクロニュースセンチメント融合）：kabusys.ai.regime_detector
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
  - 監視ダッシュボード起動用 streamlit スクリプト

環境要件（主なライブラリ）
- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリで利用）
- （実行時に必要な外部 API キーなどは環境変数で設定）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン・チェックアウト
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（pip 例）
   - pip install -r requirements.txt
   - ※ requirements.txt が無い場合は少なくとも duckdb, psutil, requests, openai, streamlit を入れてください。
4. data ディレクトリ作成
   - mkdir -p data
5. .env を作成（任意だが推奨）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
6. 主な環境変数（例）
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - MONITOR_POLL_INTERVAL=60  (監視ポーリング秒)
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag

基本的な使い方（コマンド例）
- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動: Settings に基づき sqlite (monitoring.db) を常に本番パスから開き、duckdb も接続。MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）。
  - 停止: data/stop_requested.flag を作成するとループは検知して終了します。
- Execution エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に切替えられます（本番 DB と分離）。
  - 停止: data/stop_requested.flag を作成すると実行中スレッドに停止シグナルを送り安全停止します。Execution 起動時は kill.flag のクリア設定も確認。
- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボードを表示します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD , --to YYYY-MM-DD , --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI モジュール（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — DuckDB 接続および target_date（date 型）を渡す
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。API 失敗時はフェイルセーフ（スコアを 0 にフォールバックする等）の設計です。

停止・制御ファイルについて
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がポーリング中に存在を検知すると安全に停止します（単純存在チェック）。
- data/kill.flag
  - KillSwitch が評価条件（例: ドローダウン超過等）を満たしたときに書き込むファイルで、Execution の停止トリガーとして使用できます。既に存在する場合は再書き込みしません（冪等）。
- data/execution.pid
  - ExecutionEngine の PID を書くファイル。SystemMonitor はこの PID ファイルを見てプロセス生存チェックを行います。

設定管理について（Settings）
- src/kabusys/config.py が環境変数読み込みと Settings クラスを提供します。
- 自動 env ロード: プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- KABUSYS_ENV により動作モードを `development` / `paper_trading` / `live` に切替可能。paper_trading モードでは発注先に Mock を使い DB を分離します。

重要な挙動のメモ
- Monitoring は Settings.env にかかわらず監視用 SQLite（SQLITE_PATH）を使用してログを永続化します（本番 DB を参照）。
- run_execution では `settings.paper_sqlite_path` を PAPER_TRADING 環境で使用し、本番データと分離します。
- 各モジュールは外部 API（OpenAI 等）でエラーが起きてもシステム全体が落ちないようフェイルセーフ実装（リトライやフォールバック値）になっています。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil 利用。権限や OS により失敗した場合は警告でスキップ）。

ディレクトリ構成（主要ファイル・サブパッケージの概要）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込み・Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — raw_news を OpenAI に送って ai_scores を作成
    - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite テーブル定義 / CRUD ラッパー
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を定期起動するエンジン（テスト向け run_once / 本番向け run）
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注フローの外向き API（OrderManager）
    - reconciler.py — 再起動時の注文／ポジション突合
    - ...（Broker 関連 / OrderRepository 等は同ディレクトリ内）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・丸め・キャップ適用
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / summary
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/  （実行時に使用するディレクトリ例）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - stop_requested.flag, kill.flag, execution.pid などの制御ファイル

.env の例（`.env.example` を参考に）
- KABUSYS_ENV=development
- OPENAI_API_KEY=your_openai_key
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- PAPER_FILL_MODE=instant

開発上の注意事項
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブル前提で実装されています。データが無い場合や行不足の場合は None を返す設計が多いです。
- OpenAI 呼び出しはネットワーク・429・タイムアウト等を考慮したリトライ実装が入っていますが、API キーの管理には注意してください。
- 設定や環境により発注先が実際のブローカーに切り替わるため、live モードでの実行は十分な確認と権限管理のもとで行ってください。
- 自動 .env ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml が存在するディレクトリをルートとして検出します）。テスト時に自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

トラブルシューティング（よくある質問）
- 監視ループを止めたい：data/stop_requested.flag を作成してください。スクリプトは次のポーリングで検知して終了します。
- Execution が起動しない：起動時に stop flag が立っていないか（data/stop_requested.flag）確認してください。paper_trading モードかどうかと DB パスも確認してください。
- OpenAI 呼び出しで失敗が多い：API キーのレート制限やネットワークを確認。ログにリトライ情報が出ます。

以上がプロジェクトの README 内容です。必要に応じて実際の運用手順（systemd ユニットや Dockerfile、CI 設定）を追加できます。追加で記載したい項目や、特定のコマンド例・.env のテンプレートを作成する要望があればお知らせください。