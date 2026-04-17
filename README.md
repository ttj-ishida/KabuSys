README.md

概要
---
KabuSys は日本株の自動売買・研究・監視のための軽量なツール群です。本プロジェクトには以下の主要機能が含まれます：
- 注文管理・発注エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離された DB と検証レポート生成
- DuckDB を用いたファクター計算・リサーチユーティリティ
- ニュースの NLP スコアリング（OpenAI）とレジーム判定
- Streamlit による監視ダッシュボード

主な特徴
---
- 実運用と Paper Trading を環境変数で切替可能（KABUSYS_ENV）
- 監視ログは SQLite（data/monitoring.db）へ永続化、DuckDB は価格・財務データの分析用
- LINE へのプッシュ通知、kill.flag による ExecutionEngine の安全停止
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）と市場レジーム判定
- Portfolio 構築/サイズ決定/セクター制限などの純関数群を提供（テストしやすい）

必要条件
---
- Python 3.10+
- 外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリで利用可能）
- （任意）LINE チャンネル・OpenAI API キーなど外部サービスの資格情報

セットアップ手順
---
1. リポジトリをクローン、プロジェクトルートへ移動
   - ルートに .git または pyproject.toml があることを前提に Settings はプロジェクトルートを自動検出します。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例: pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数 / .env を準備
   - ルートに .env（または .env.local）を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化可）。
   - 必須の主要環境変数例（.env.example を参照してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（ai 機能を使用する場合）
     - KABUSYS_ENV (development | paper_trading | live)
   - 主要 DB / ファイルパスはデフォルトで data/ 配下に保存されます（下記参照）。

環境変数の主な設定
---
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（ai/news/regime 機能で必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — 監視は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定動作（instant|partial|never|reject）

使い方
---

基本的な実行方法
- 実行スクリプトはパッケージモジュールとして実行できます（プロジェクトルートから）:

1) 監視プロセスを起動（SystemMonitor の単独ポーリングループ）
   - python -m kabusys.run_monitoring
   - 説明: 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔を上書き可能（デフォルト 60 秒）。
   - stop: プロジェクトルート/data/stop_requested.flag を作成するとループ終了します。

2) ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - 説明: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に保存して本番 DB と分離します。
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
   - 停止は stop_requested.flag の作成で検出して安全に停止します（ExecutionEngine 側で engine.stop() が呼ばれる）。

3) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）

4) 監視ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite を開きダッシュボードを表示します。

5) AI / レジーム機能
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
   - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用します。

停止・フラグファイル
---
- data/stop_requested.flag: run_monitoring / run_execution がループ内でチェックする外部停止フラグ（任意のファイル内容で可）。存在するとループを終了（安全停止）します。
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に対する停止要求）。kill.flag は KillSwitch.clear() で削除可能。
- data/execution.pid: ExecutionEngine が起動時に PID を書き込み、SystemMonitor はこの PID を監視してプロセス生存チェックを行います。

内部 DB の分離
---
- 監視ログ: data/monitoring.db（Settings.sqlite_path）。Monitoring は常に本番 sqlite_path を使用します。
- Paper Trading: data/paper_trading.db（Settings.paper_sqlite_path） — KABUSYS_ENV=paper_trading の場合に使用。
- DuckDB: data/kabusys.duckdb（価格・財務データ・raw_news などの分析用）

主な CLI / エントリポイント一覧
---
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution
- python -m kabusys.tools.paper_verification_report
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理（.env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py  — ExecutionEngine 起動スクリプト

サブパッケージ:
- /ai
  - news_nlp.py        — ニュースセンチメント（OpenAI）処理
  - regime_detector.py — 市場レジーム判定（OpenAI + 1321 MA200）
- /monitoring
  - monitoring_db.py     — SQLite スキーマと読み書き用クラス
  - system_monitor.py    — CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py     — 注文滞留・約定異常検出
  - risk_monitor.py      — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor の束ね（テスト用 run_once / 本番 run）
  - alert_manager.py     — LINE への通知送信（クールダウン管理）
  - kill_switch.py       — KillSwitch（kill.flag 書き込み）
  - streamlit_dashboard.py — Streamlit ダッシュボード
- /execution
  - order_manager.py
  - reconciler.py
  - order_repository.py (他、発注関連実装)
  - execution_engine.py (Engine 実装)
- /portfolio
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- /research
  - factor_research.py
  - feature_exploration.py
- /tools
  - paper_verification_report.py
- /utils
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発メモ / 注意事項
---
- Settings はプロジェクトルートの .env/.env.local を自動読み込みします。OS 環境変数が優先され、.env.local は上書きで読み込まれます。テスト等で自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードでは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI の呼び出しはリトライ（指数バックオフ）やエラーハンドリングを行いますが、API キーの漏洩や利用料には注意してください。
- process_priority.set_process_priority() により起動時にプロセス優先度を上げますが、権限や OS により実行できないことがあります（警告ログにて通知）。
- DuckDB / SQLite のバージョンや接続方法（URI）に注意してください。streamlit_dashboard では read-only URI モードで接続します。
- Paper 検証レポートは DB 内に必要なテーブル（system_status, trade_logs, risk_logs, ai_scores など）が存在することを前提としています。存在しない場合は N/A を返す箇所があります。

ライセンス・貢献
---
- 本リポジトリに LICENSE ファイルがある場合はその指示に従ってください。バグ報告・機能提案はプルリクまたは Issue を通してください。

付録：よく使うコマンド例
---
- 監視（デフォルト設定、60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上。README の改善点や追加して欲しい情報（例: サンプル .env、CI 設定、テスト実行方法）があれば教えてください。