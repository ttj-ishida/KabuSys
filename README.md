KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ライブラリ群です。  
主要機能は次の通りです。

- 実行エンジン（ExecutionEngine）による注文管理・発注
- 監視サブシステム（MonitoringEngine）によるプロセス／データ／注文監視・アラート
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュース NLP を使った銘柄センチメント評価（OpenAI）
- 市場レジーム判定（MA + LLM 結合）
- Paper Trading 向けの検証・レポート出力ツール
- Streamlit ベースの監視ダッシュボード

このリポジトリはライブラリ実装（src/kabusys）と複数のスクリプト / ツール群を含みます。

主な機能一覧
------------
- execution
  - OrderManager / ExecutionEngine / Reconciler：注文ライフサイクルと再起動時の同期
  - Broker クライアントファクトリ（本番 / モックを切り替え）
- monitoring
  - SystemMonitor：CPU/MEM/DISK/プロセス生存・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常監視
  - RiskMonitor：ドローダウン/ポジション上限監視とリスクログ
  - MonitoringDB：SQLite に監視ログを永続化
  - AlertManager：LINE Push による通知（クールダウン付き）
  - KillSwitch：flag ファイルによる ExecutionEngine 停止トリガ
  - Streamlit ダッシュボード（監視 DB を可視化）
- research
  - factor_research：モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC 等
- portfolio
  - 候補選定、重み計算、セクター制約、ポジションサイズ計算
- ai
  - news_nlp：ニュース記事を OpenAI でセンチメント評価して ai_scores に格納
  - regime_detector：ETF の MA とマクロ NLP を組み合わせたレジーム判定
- tools
  - paper_verification_report：paper trading 用 DB から検証レポートを出力

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone ... && cd repo

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低限の依存（本プロジェクトの実行に必要な代表パッケージ）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード使用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨します。

4. データディレクトリの作成
   - mkdir -p data
   - デフォルトでは SQLite / DuckDB ファイルは data 以下に作成されます。

5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（デフォルトは括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — OpenAI を使う機能で必要
     - LOG_LEVEL (INFO)
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト: instant
     - PID_FILE_PATH (data/execution.pid)
     - KILL_FLAG_PATH (data/kill.flag)
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で上書き可）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効にする（テスト用）

   - .env の簡単な例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - OPENAI_API_KEY=sk-xxxx
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

使い方（主要スクリプト / ツール）
-------------------------------

- 監視プロセス起動（SystemMonitor 単体のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止方法: data/stop_requested.flag を作成するとループが検出して終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 実行中は PID を data/execution.pid に書きます。停止は data/stop_requested.flag を作成するか、プロセスに SIGINT を送る（Ctrl+C）。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力例: 注文成功率、送信率、レイテンシ（P95）等の集計と PASS/FAIL 判定

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用モードで開き、Overview/Positions/Orders/System タブを表示します。

- AI 関連（ニュース NLP / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して実行（OpenAI API key は引数 or OPENAI_API_KEY）
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロ NLP を使って market_regime テーブルに書き込みます
  - これらは OpenAI API を呼ぶため API キーが必要です。

- 停止フラグ / KillSwitch
  - KillSwitch はリスク閾値（ドローダウン等）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 系スクリプトは起動時に kill.flag が既にある場合は起動を拒否する挙動があります。

運用上の注意
------------
- Monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path（設定による）を使います（監視ログは本番 DB に混ざらないように注意）。
- run_execution は KABUSYS_ENV=paper_trading の場合、本番 DB と分離された paper_trading DB を使用します。
- process 優先度設定（高）・CPU affinity 設定は psutil を使います。権限がない環境では警告が出ますが処理は継続します。
- DuckDB を使って時系列データや raw_financials を扱うため、事前に prices_daily / raw_financials / raw_news 等のテーブルを準備してください（データ投入は別途の ETL を想定）。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

- execution/
  - order_manager.py
  - order_repository.py
  - execution_engine.py
  - reconciler.py
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - ...

- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- monitoring/（上記に含まれる）
- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - process_priority.py
  - __init__.py

主要な設計方針（簡潔に）
------------------------
- データ処理・リサーチ機能は DuckDB を用いてローカル SQL で完結させる（外部 API への依存を最小化）。
- 監視ログは SQLite（軽量 DB）へ永続化。監視系と注文系の DB は用途に応じて分ける（paper_trading 用 DB も用意）。
- OpenAI（LLM）を用いる箇所はフェイルセーフ設計（API 失敗時はデフォルト値で継続、限定的にリトライ）。
- モジュールはユニットテストしやすいよう純粋関数/副作用の少ない設計を意識。

よく使うコマンド（例）
---------------------
- 監視ループを起動：
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- ExecutionEngine（paper_trading）を起動：
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス・貢献
----------------
- 本 README にライセンス情報が含まれていない場合はリポジトリのトップレベルにある LICENSE を参照してください。  
- バグ報告・改善提案は Issue / Pull Request で受け付けます。

補足
----
- ソース内ドキュメント（docstrings）に詳細な使用法や設計意図が書かれています。実装を変更する際は docstrings とスキーマ（DB テーブル定義）の整合性に注意してください。
- 本 README はコードベースの主要点をまとめたものであり、個別モジュールの詳細な API については該当ソースを参照してください。