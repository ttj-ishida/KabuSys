KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。本リポジトリには、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・ニュース NLP（LLM）連携など、実運用を想定した多数のモジュールが含まれています。設計上、次の点を重視しています。

- 本番と paper_trading（バックテスト/検証）を分離する設計
- DuckDB / SQLite を用いたデータ分析・永続化
- OpenAI API を用いたニュースセンチメント評価（フェイルセーフ実装）
- モジュール分割によるテスト容易性（純粋関数群・DB 経由の永続化層の分離）

主な機能
--------
- Execution（発注）関連
  - OrderManager / ExecutionEngine（発注・状態管理・リスク管理・再同期ロジック）
  - Reconciler（再起動時の注文・ポジション照合）
  - Broker クライアント抽象化（paper_trading では MockBrokerClient が利用される）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視（アラートや kill flag 発動）
  - AlertManager：LINE Push によるプッシュ通知（クールダウン付き）
  - MonitoringEngine / streamlit ダッシュボード

- Portfolio（銘柄選定・配分）
  - 候補選定、等重・スコア重み付け、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算（単元・集計キャップ対応）

- Research（調査用）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン・IC（Information Coefficient）・統計サマリ

- AI（LLM）
  - news_nlp：ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に保存
  - regime_detector：ETF（1321）の MA とマクロニュースの LLM センチメントを合成して日次の市場レジームを判定し market_regime に書込

- ユーティリティ
  - process_priority：プロセス優先度 / CPU affinity の設定ユーティリティ
  - 環境変数ローダ（.env / .env.local 自動ロード）

セットアップ
----------
前提
- Python 3.10+（型ヒントにより 3.10+ を想定）
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
  - （必要に応じて）その他のブローカー SDK 等

推奨手順（UNIX 系シェル例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそちらを使ってください）
   - pip install duckdb psutil openai requests streamlit

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を直接エクスポートしてください。
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

注記:
- .env の自動読み込みは Settings モジュールで実装されています（プロジェクトルートが検出できる場合）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（実行例）
----------------

1) 監視プロセスを起動する
- 簡易（デフォルトのポーリング間隔 60秒）:
  - python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で上書き:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - プロジェクトルートに data/stop_requested.flag を作成すると監視ループは終了します（run_monitoring/run_execution ともにチェックします）。

2) ExecutionEngine（発注エンジン）を起動する
- 本番/開発/検証の切替:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 説明:
  - paper_trading 環境では MockBrokerClient が利用され、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
  - run_execution は起動時に data/execution.pid を作成し、停止時に stop flag（data/stop_requested.flag）を検出すると安全に停止します。

3) Paper Trading 検証レポート生成（ツール）
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) 監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは read-only で SQLite を開き、直近のポジション・注文・システムステータス・リスクログを表示します。

5) AI（ニューススコア / レジーム判定）
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け取る API です。OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定します。
- 例（スクリプトや REPL 内で）:
  - from openai import OpenAI  # 実装は内部で OpenAI クライアントを生成します
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="sk-...")

注意点・運用上のポイント
-----------------------
- MONITORING は常に Settings.sqlite_path（production 想定）を使用するため、運用時は DB のパスに注意してください。paper_trading は run_execution 側で分離されます。
- OpenAI コールは失敗に対してリトライ・フェイルセーフ（score_news は失敗時にそのチャンクをスキップ、regime_detector は macro_sentiment=0.0 で継続）を組み込んでいますが、APIキーやレート制限の管理は運用側で行ってください。
- kill switch:
  - RiskMonitor／KillSwitch により重大事象発生時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です。手動でクリアする場合はファイルを削除してください。
- PID／stop フラグ:
  - 実行中は data/execution.pid（ExecutionEngine）が作成されます。run_monitoring/run_execution は data/stop_requested.flag を検出して終了します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / .env ロード / Settings
- run_monitoring.py               — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

サブパッケージ（抜粋）
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory.py (参照あり)
  - ...（発注関連実装）

- monitoring/
  - monitoring_db.py               — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
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

- utils/
  - process_priority.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

data/（実行時に使用するファイル・想定）
- data/monitoring.db               — SQLite（monitoring 用, デフォルト）
- data/paper_trading.db            — SQLite（paper_trading 用, デフォルト）
- data/kabusys.duckdb              — DuckDB のデータファイル（デフォルト）
- data/execution.pid               — ExecutionEngine の PID（起動時に作成）
- data/stop_requested.flag         — 起動中プロセス停止のためのフラグ（手動作成で停止）
- data/kill.flag                   — KillSwitch が書き込む停止フラグ（自動生成）

開発・テストに関するメモ
------------------------
- portfolio/*、research/* の多くは純粋関数（DB 参照なしまたは DuckDB 接続を受ける）として実装されており、ユニットテストが容易です。
- AI API 呼び出し部は個別関数（_call_openai_api）でラップしているため、テスト時はモック置換（unittest.mock.patch）で外部依存を切り離せます。
- monitoring_db.init_monitoring_db は冪等にテーブル・インデックス作成・簡易マイグレーション（カラム追加）を行います。初回起動時に DB が準備されます。

追加情報
--------
- Settings クラスでサポートされる KABUSYS_ENV 値: development, paper_trading, live
- PAPER_FILL_MODE（paper_trading 用）の有効値: instant, partial, never, reject
- log レベルは LOG_LEVEL 環境変数で設定可能（DEBUG, INFO, WARNING, ERROR, CRITICAL）

貢献・ライセンス
----------------
- このリポジトリの貢献ルール・ライセンスは本 README に明記していません。利用・改変・再配布を行う場合はプロジェクト管理者に確認してください。

お問い合わせ
------------
- 実装上の詳細や動作確認について質問があれば、使用箇所（例: どのモジュールを起動したいか、設定ファイルの中身など）を教えてください。必要に応じて起動コマンドや .env の具体例を提示します。