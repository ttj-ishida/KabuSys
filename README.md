README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための内部ライブラリ群です。
- 戦略（ファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 実行基盤（ExecutionEngine、OrderManager、Reconciler）
- 監視（System / Trade / Risk モニタ、アラート、ダッシュボード）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- ツール（Paper Trading 検証レポートなど）

このリポジトリは純粋関数的な計算モジュールと、実行／監視用のランタイムスクリプトを含みます。

主な機能
--------
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- portfolio:
  - 候補選定、等配分／スコア加重配分、セクター制約、レジーム乗数
  - ポジションサイズ計算（ロット丸め、リスクベース、利用可能現金キャップ）
- execution:
  - OrderManager、OrderRepository、ExecutionEngine、Reconciler（再起動時の同期）
  - Broker クライアントの抽象化（paper_trading 時は Mock を使用）
- monitoring:
  - SystemMonitor（プロセス稼働・データ鮮度・リソース監視）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件により停止フラグを書き込み）
  - AlertManager（LINE へのプッシュ通知）
  - Streamlit ダッシュボード（監視 DB を可視化）
- ai:
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に格納
  - マクロ + ETF MA200 を用いた市場レジーム判定
- tools:
  - paper_verification_report: Paper Trading の検証レポート生成

依存ライブラリ（代表）
--------------------
実行に必要となる主なパッケージ（requirements.txt は含まれていない想定のため、参考）:
- duckdb
- psutil
- openai
- requests
- streamlit
- sqlite3（標準ライブラリ）
- その他：Python 3.9+ を想定

セットアップ手順
--------------
1. Python 環境作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がある場合）
   - pip install -r requirements.txt
   - または手動で必要パッケージをインストール:
     pip install duckdb psutil openai requests streamlit

3. プロジェクトルートに .env（または .env.local）を用意
   - .env.example を参考に環境変数を設定してください（本リポジトリに .env.example が存在する前提）。
   - 自動ロード挙動:
     - デフォルトで .env/.env.local がプロジェクトルートから自動読み込みされます。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（よく使うもの）
------------------------------
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は MockBroker を使用し、paper 用 DB に書き込む。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所があれば設定）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）用（任意）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用ファイルパス（デフォルトは data 以下）

使い方（コマンド/スクリプト）
--------------------------

1) 監視ループの起動（Monitoring）
- 監視モジュール単体で SQLite にログを取り続けるスクリプト:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
- 注意:
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループが検出して終了します。

2) ExecutionEngine（発注エンジン）の起動
- python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中にプロセスを停止したい場合は data/stop_requested.flag を作成するとエンジンを停止します。
  - KillSwitch により data/kill.flag を書き込まれると ExecutionEngine 側で停止処理が走ります（kill.flag は Settings.kill_flag_path）。

3) Streamlit ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB を read-only で開いてダッシュボードを表示します。MonitoringEngine が DB を更新している前提です。

4) Paper Trading 検証レポート生成
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD  レポート開始日
    --to   YYYY-MM-DD  レポート終了日
    --db PATH          SQLite DB ファイル（優先順位: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

5) AI モジュール（プログラム利用）
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  # api_key 指定がなければ OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- 注意:
  - API キーが未設定の場合、関数は ValueError を投げます（明示的に api_key を渡すか環境変数を設定してください）。
  - LLM 呼び出しに失敗した場合はフォールバック動作（例: macro_sentiment=0）で処理継続する設計になっています。

運用時のファイル / フラグ
------------------------
- data/stop_requested.flag
  - run_monitoring / run_execution が監視しており、存在を検知するとループ／スレッドを停止します。
- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込むファイル。ExecutionEngine 側に停止シグナルを送る用途。
  - clear: KillSwitch.clear() を呼ぶか、ファイルを手動で削除してください。
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル。SystemMonitor はこのファイルを監視してプロセス生存をチェックします。

開発・デバッグのヒント
---------------------
- .env 自動読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- process priority / cpu affinity の設定は psutil を利用します。権限不足により設定が失敗する場合がありますが、ログに警告が出てスキップされます。
- duckdb / sqlite のパスは Settings クラス経由で取得できます。実行時にパスを上書きしたい場合は環境変数を利用してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定の集中管理（.env 自動ロード含む）
- run_monitoring.py               — SystemMonitor のポーリング起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                    — ニュースセンチメント評価（OpenAI）
  - regime_detector.py             — 市場レジーム判定（MA200 + マクロLLM）

- monitoring/
  - monitoring_db.py               — SQLite に対する永続化層（テーブル初期化 + CRUD）
  - system_monitor.py              — システム・データ鮮度監視
  - trade_monitor.py               — 注文滞留・約定異常検出
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - kill_switch.py                 — 停止フラグ管理（kill.flag）
  - alert_manager.py               — LINE 通知ラッパー
  - monitoring_engine.py           — 各モニタを束ねる実行エンジン
  - streamlit_dashboard.py         — Streamlit ダッシュボード

- execution/
  - execution_engine.py            — 実行エンジン本体（EngineConfig など）
  - order_manager.py               — 注文状態遷移管理の外向き API
  - order_repository.py            — Orders DB 操作（SQLite）
  - reconciler.py                  — 再起動時の状態同期ロジック
  - broker_factory.py              — Broker クライアント生成（環境により Mock/実ブローカー）

- portfolio/
  - portfolio_builder.py           — 候補選定・重み計算
  - position_sizing.py             — 株数計算・キャップ・ロット丸め
  - risk_adjustment.py             — セクターキャップ・レジーム乗数

- research/
  - factor_research.py             — モメンタム/ボラティリティ/バリューファクター
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー

- tools/
  - paper_verification_report.py   — Paper Trading の検証レポートスクリプト

- utils/
  - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

付記（注意事項）
----------------
- 実行前に .env（または環境変数）で必要な認証情報（OPENAI_API_KEY, KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN 等）を設定してください。
- Paper Trading モードは実ブローカーへのアクセスを行わないため、検証やローカルテストに適しています。paper_trading 時は PAPER_TRADING_SQLITE_PATH にデータが書き込まれます。
- OpenAI 呼び出しは外部ネットワークリクエストです。API 利用量・レート制限に注意してください。
- 監視・実行プロセスは PID ファイルやフラグファイルを使ってプロセス間でやり取りしています。手動でファイル操作する際は競合に注意してください。

以上が本コードベースの主要な使い方・構成の説明です。必要であれば各モジュールの API や設定項目（Settings クラスのプロパティ一覧）を README に追記できます。