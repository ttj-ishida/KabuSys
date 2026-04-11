README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリ（src/kabusys）には以下の主要機能が含まれます:

- Execution: シグナルに基づく発注エンジン（ExecutionEngine、OrderManager 等）
- Monitoring: システム稼働・注文・リスク監視とアラート（LINE 経由の通知、Streamlit ダッシュボード）
- Portfolio: 銘柄選定・ウェイト計算・ポジションサイズ算出（等配分・スコア加重・リスクベース等）
- Research: ファクター計算・将来リターン・IC 計算・統計集計
- AI: ニュースの NLP スコアリング、マクロニュース＋ETF MA を使った市場レジーム判定（OpenAI API 利用）
- Utils: プロセス優先度設定、設定管理（.env 自動読み込み）など

主な特徴
-------
- ExecutionEngine による安全な発注フロー（DB 永続化を考慮した状態遷移、再起動時のリコンシリエーション）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と KillSwitch による自動停止／アラート
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials などのテーブル想定）
- OpenAI を用いたニュースセンチメント評価（バッチ・リトライ・レスポンス検証実装）
- Streamlit で可視化できる監視ダッシュボード
- Paper trading 用に本番 DB と分離した動作モード

前提・依存
-----------
（最小限の推奨パッケージ。プロジェクト側で requirements.txt を用意している場合はそちらを使用してください。）

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (AI モジュール利用時)
- sqlite3（標準ライブラリ）
- その他: logging, datetime, pathlib など標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローン（またはパッケージ配布を展開）
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

   （テスト用や他機能を使う場合に追加パッケージが必要になることがあります）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（config.py による自動読み込み）。
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD      — kabu ステーション API のパスワード（必須）
     - KABUSYS_ENV            — 実行環境: development | paper_trading | live （デフォルト: development）
     - OPENAI_API_KEY         — OpenAI API を使う場合に必要
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxx
     KABU_API_PASSWORD=yyy
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...

5. データディレクトリの用意
   - デフォルトで使用する DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading sqlite: data/paper_trading.db
   - 必要に応じてディレクトリを作成してください:
     - mkdir -p data

使い方
------
エントリポイント（スクリプト）を使った起動:

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 実行時に Settings（環境変数）を参照します。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使い、MockBroker を利用する想定です。

- SystemMonitor を単独でポーリングで起動（MonitoringEngine と組み合わせて使用する）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用します（監視 DB は本番を参照する意図）。

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

AI / 研究系の関数をプログラムから呼ぶ例:

- ニューススコア算出（DuckDB 接続を作成して呼ぶ）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- レジーム判定（market_regime 書き込み）
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- ファクター計算（research）
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026,3,20))

注意点 / 実行時ヒント
--------------------
- Settings（kabusys.config.Settings）は .env 自動ロード機能を持ちます。テストで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV:
  - development: 開発モード（デフォルト）
  - paper_trading: paper trading（発注はモック・paper DB を使用）
  - live: 本番モード
- run_execution 実行時は PID ファイル（settings.pid_file_path, デフォルト data/execution.pid）を書きます。run_monitoring は PID を監視してプロセス生存を判定します。
- kill.flag（settings.kill_flag_path, デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- OpenAI を使う機能は API キーが必要です。API 呼び出しの失敗時はフェイルセーフ（スコア 0.0 等で継続）する実装が多く組み込まれていますが、API 利用料に注意してください。
- Monitor/Engine はプロセス優先度を high に切り替えようとします（psutil を使用）。権限がないと警告になりますが致命的ではありません。

主要ファイルとディレクトリ構成
----------------------------
以下は src/kabusys 以下の代表的な構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・.env 読み込み設定
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - broker_api.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
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

よくある質問（FAQ）
------------------
Q: paper_trading モードで本番 DB に影響はありますか？
A: paper_trading の場合、run_execution は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため、本番監視 DB（data/monitoring.db）とは分離されます。ただし Monitoring は本番 sqlite_path を参照するため、監視と実行の DB は別管理が推奨されます。

Q: MONITOR_POLL_INTERVAL はどこで設定しますか？
A: 環境変数 MONITOR_POLL_INTERVAL（秒）で指定します。整数で 1 以上を指定してください。不正な値は 60 秒にフォールバックします。

Q: Streamlit ダッシュボードが DB を開けないと言われます
A: 監視ダッシュボードは監視プロセスが DB を作成・更新していることを前提にします。MonitoringEngine を先に起動して monitoring.db を作成してください。streamlit 実行時に --db オプションでパスを指定できます（例: --db data/monitoring.db）。

貢献・開発
----------
- 新しい機能追加やバグ修正は PR を送ってください。
- テスト・CI がある場合はそちらの規約に従ってください。
- .env.example をプロジェクトルートに作成して重要な環境変数の雛形を配布することを推奨します（config.py 内メッセージ参照）。

ライセンス
---------
（ここにプロジェクトのライセンス表記を入れてください。例: MIT）

補足
----
この README は src/kabusys 内のコードから抽出した設計と使用方法に基づいています。実行環境や運用方針に応じて設定（DB の場所、LINE 通知設定、OpenAI API 利用等）を適切に管理してください。必要に応じて .env.example、requirements.txt、デプロイスクリプト等を追加して整備してください。