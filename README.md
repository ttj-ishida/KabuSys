KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python コードベースです。  
主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）による発注・注文管理・リスク制御
- 監視（MonitoringEngine）によるシステム稼働状況・注文異常・リスクの定期チェック
- ポートフォリオ構築ユーティリティ（銘柄選定、配分、ポジションサイジング、セクター制限）
- ファクター計算・リサーチツール（モメンタム、ボラティリティ、バリューなど）
- AI モジュール（ニュースのセンチメント評価、レジーム判定） — OpenAI（gpt-4o-mini）を利用
- Paper Trading 用検証・レポート生成ツール
- Streamlit ベースの監視ダッシュボード（read-only）

特徴
----
- 設定は環境変数（.env/.env.local 自動ロード）で管理
- 本番／開発／Paper Trading を KABUSYS_ENV で切り替え（development / paper_trading / live）
- 監視ログは SQLite（data/monitoring.db など）に永続化。DuckDB は時系列データやファクター計算に利用
- OpenAI 呼び出しはリトライ・バリデーション・スコアクリップ等の堅牢な実装
- プロセス優先度・CPU affinity 設定ユーティリティで実行環境に配慮

セットアップ手順
----------------

前提
- Python 3.9+（typing の一部記法や pathlib 等を使用）
- system パッケージ: duckdb, psutil, requests, openai, streamlit（ダッシュボードを使う場合）
  例: pip install duckdb psutil requests openai streamlit

推奨手順
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd your-repo

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows は .venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  # 監視ポーリング間隔（秒）

5. データディレクトリ等を作成
   - mkdir -p data

使い方
------

主要スクリプト
- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
    - 監視ループを起動します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依存しない）。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
    - 起動時に ExecutionEngine のセッションを開始します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
    - 期間を指定して稼働率・注文成功率・レイテンシ等のレポートを標準出力に出します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - Read-only モードで SQLite を URI 経由で読み込み表示します。MonitoringEngine を先に起動してデータを作ってください。

環境切替（Paper Trading）
- Paper Trading を使うには KABUSYS_ENV=paper_trading を設定して run_execution を起動します。Paper 環境では broker はモックが使われ、取引ログは data/paper_trading.db に記録されます。
- PAPER_FILL_MODE（instant|partial|never|reject）で約定の振る舞いを制御できます。

監視・アラート
- AlertManager は LINE Messaging API を使ったプッシュ通知を行います（channel token / user id が空の場合は送信しません）。
- KillSwitch は監視の結果により data/kill.flag を書き込み、ExecutionEngine 停止のシグナルを送ります。
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、KillSwitch・AlertManager と連携してアラートや停止判定を行います。

API キー（OpenAI 等）
- ai/news_nlp.py / ai/regime_detector.py は OpenAI API を利用します。OPENAI_API_KEY を環境変数に設定するか、モジュール関数呼び出し時に api_key 引数で渡してください。
- API 呼び出しは 429／タイムアウト／5xx に対してリトライ実装を持ち、レスポンスのバリデーションも行います。

重要な挙動
- 実行時に set_process_priority("high") を呼んでプロセス優先度を可能な範囲で高めます（環境によって失敗した場合は警告ログのみ）。
- Settings モジュールは自動でプロジェクトルートの .env/.env.local を読み込みます（CWD に依存せず __file__ の親を探索します）。
- MonitoringDB.init_monitoring_db() はテーブルの作成と一部カラムのマイグレーション（必要なら ALTER TABLE）を行います（冪等）。

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート生成
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py           — システム状態・データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — kill.flag 管理
  - alert_manager.py            — LINE 通知ラッパー
  - monitoring_engine.py        — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py      — Streamlit ダッシュボード（起動スクリプト）
- execution/
  - order_manager.py
  - reconciler.py
  - ...（OrderRepository, broker など発注関連コンポーネント）
- portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 株数決定・スケーリング
  - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - __init__.py
- research/
  - factor_research.py          — モメンタム／ボラティリティ／バリュー等
  - feature_exploration.py      — 将来リターン, IC, 統計サマリー
  - __init__.py
- ai/
  - news_nlp.py                 — ニュースセンチメント（OpenAI）
  - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
  - __init__.py
- utils/
  - process_priority.py         — 優先度・CPU affinity ユーティリティ
  - __init__.py
- data/                         — 実運用では data/kabusys.duckdb, data/monitoring.db 等が置かれる想定

データベース（主なテーブル）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の単一レコードに集計を保持)

開発・テスト時のヒント
- Settings は自動で .env をロードするため、テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI 呼び出しはモジュール内でラップされているため、ユニットテストでは該当関数（_call_openai_api など）をパッチしてモックできます。
- MonitoringEngine.run_once() を使うとテスト用に一回だけ監視処理を実行できます。

ライセンス／バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期値）です。ライセンス情報はリポジトリに含めてください（本 README には未記載）。

補足（よくある質問）
- Q: MONITOR_POLL_INTERVAL に 0 や負の値を設定したら？
  - A: 0 以下は無効と見なされ、デフォルト 60 秒にフォールバックします（ログに警告が出ます）。

- Q: Paper Trading と本番 DB の分離はどうなっているの？
  - A: KABUSYS_ENV=paper_trading のとき run_execution は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番の sqlite_path とは別ファイルを使います。

お問い合わせ
------------
実装の詳細確認や追加機能の提案はソースコードの該当モジュール（monitoring/, execution/, ai/, portfolio/, research/）を参照してください。README に含めてほしい追加情報や、導入ガイドのテンプレートが必要であればお知らせください。