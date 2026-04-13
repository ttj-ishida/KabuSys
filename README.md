KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリには次の主要機能を含みます。

- 注文発行・状態管理・再同期を行う Execution Engine
- モニタリング（システム状態、注文滞留、リスク監視）とアラート送信（LINE）
- Paper Trading 用の検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP を用いた銘柄センチメントスコアリング / レジーム判定（OpenAI 利用）
- Streamlit ベースの監視ダッシュボード

主な設計方針
- 多くの処理は純粋関数または DB 層と分離して実装（テスト容易性）
- Paper Trading は本番データベースと完全に分離（別 SQLite ファイル）
- ルックアヘッドバイアス回避のため日付参照に注意（date.today() を安易に参照しない実装）

機能一覧
-------
- Execution
  - 注文作成 / 送信 / 同期 / 再コンシリエーション（Reconciler）
  - リスク管理（RiskManager）、OrderManager、OrderRepository 等
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: フラグファイルで ExecutionEngine に停止シグナルを送信
  - AlertManager: LINE Messaging API での通知
  - MonitoringEngine: 上記をまとめて定期実行
  - Streamlit ダッシュボードで可視化
- Research / Portfolio
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）算出
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約適用
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事をまとめて LLM に渡し銘柄ごとのスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースから市場レジーム判定を行い market_regime テーブルへ記録
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート（稼働率・成功率・レイテンシ等）

依存関係（主なライブラリ）
-------------------------
少なくとも次のライブラリが必要です（プロジェクトの requirements.txt を用意してください）:

- python >= 3.9（型ヒントに Path | None 等を使用）
- duckdb
- psutil
- requests
- openai
- streamlit

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリに入る
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を使用してください。

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋）
-----------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH が使用され MockBroker を使う設計になっています。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（Ai 機能を使う場合に必須）
- PAPER_FILL_MODE: Paper Trading のフェイルモード（instant / partial / never / reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60。0以下は無効扱いでデフォルトにフォールバック）

使い方（主要な起動方法）
-----------------------

1) Monitoring（常駐監視）を起動する
- python -m kabusys.run_monitoring
  - 動作: Settings を読み、プロセス優先度を "high" に設定し（可能なら）、監視用 SQLite を開いて SystemMonitor のポーリングループを開始します。
  - MONITOR_POLL_INTERVAL の値でポーリング間隔を調整できます（秒）。

2) Execution Engine を起動する
- python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合は paper 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使うように設計されています。
  - 実行前に必要な環境変数（KABU_API_PASSWORD 等）を設定してください。
  - 起動時に PID ファイル（Settings.pid_file_path）を書き込む挙動を想定しています。

3) Streamlit 監視ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いて、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。
  - レポートは標準出力に印字され、稼働率・注文成功率・送信率・レイテンシ等を評価します。

5) AI 系処理（プログラム内から呼び出す）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB コネクションを渡して実行。api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）MA とマクロニュースを使って market_regime テーブルにレジームを書き込みます。

運用上の注意
------------
- Monitoring は常に本番用の sqlite_path を使う設計です（KABUSYS_ENV に依存しません）。
- Paper Trading は本番 DB と分離するため PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で失敗することがあります（権限不足など）。失敗時は警告ログが出ますが処理は継続します。
- OpenAI を使う機能は API の呼び出しに失敗した場合、フェイルセーフとしてスコアを 0.0 に置くなどの挙動で継続する設計です（完全な例外停止を避ける）。
- kill.flag の存在で ExecutionEngine を停止させる仕組みを持っています。Execution 側はこのファイルの存在を確認して安全に停止する必要があります。

データベースと初期化
--------------------
- init_monitoring_db(conn) により monitoring 用 SQLite のテーブルが冪等的に作成されます（system_status, trade_logs, positions, risk_logs, dashboard など）。
- DuckDB は prices_daily / raw_financials 等を前提とする関数群（research／ai）が参照します。DuckDB ファイルパスは DUCKDB_PATH で指定してください。

ディレクトリ構成（抜粋）
-----------------------
下記は主要ファイル／ディレクトリの一覧（src/kabusys 以下）。実際のリポジトリには他のモジュールやデータディレクトリが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                              — 環境変数/設定管理
  - run_monitoring.py                      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                       — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py                  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                     — SQLite 永続化層（init, MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_api, order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py

開発メモ / よくある質問
----------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は整数秒で設定してください。不正値や 0 以下はデフォルト（60 秒）にフォールバックします。
- Monitoring 起動時は PID ファイルや kill.flag の取扱いに注意してください（権限、ファイルシステムのパーミッション等）。
- DuckDB や SQLite の接続はファイルパスで行われます。複数プロセスから同時書き込みする際の競合に注意してください（monitoring は読み書き、streamlit は読み取り専用で開くなど）。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を追記してください）

以上。必要であれば README にサンプル .env の例や systemd / supervisor 用のサービスユニット例、より詳細な API ドキュメント（各モジュールの振る舞い、戻り値の詳細）を追加できます。どの部分を詳しく書けば良いか教えてください。