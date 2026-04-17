# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。
このリポジトリはエンジン本体（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB ベースのファクター計算）、AI を用いたニュース評価などの機能を含みます。

以下はコードベースから抜粋した README（日本語）です。

主なポイント
- 実行/監視プロセスは SQLite（監視ログ）と DuckDB（時系列データ・ファクター計算）を利用します。
- KABUSYS_ENV により環境を切り替え可能（development / paper_trading / live）。
- paper_trading モードでは MockBroker を使用し、paper_trading 専用の SQLite DB に記録して本番 DB と分離します。
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定機能を提供します（API キー必要）。
- LINE Messaging API を用いたアラート送信機能を持ち、kill flag による ExecutionEngine 停止をサポートします。

機能一覧
- Execution（発注エンジン）
  - ExecutionEngine 起動スクリプト: kabusys.run_execution
  - BrokerFactory による実環境 / モック分岐（KABUSYS_ENV）
  - OrderManager / OrderRepository / Reconciler による状態管理・再同期機能
  - リスク管理（RiskManager）による発注制限

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス PID、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 条件により停止フラグを書き込み、LINE 通知を実施
  - run_monitoring スクリプトでポーリング実行（MONITOR_POLL_INTERVAL 環境変数で間隔変更可能）
  - Streamlit ダッシュボード（監視用）: src/kabusys/monitoring/streamlit_dashboard.py

- Portfolio（銘柄選定・配分・株数）
  - 選定・等分配・スコア加重・リスク調整（セクターキャップ・レジーム乗数）
  - 単元株丸め・投下資金スケールダウン処理

- Research（DuckDB ベース）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）・特徴量サマリ等のユーティリティ

- AI（OpenAI 統合）
  - news_nlp.score_news: raw_news を LLM に渡して銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを合成して market_regime テーブルへ書き込み

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等を集計）
    - 合格基準の一例: 稼働率 >= 99%、fill_rate >= 90%、P95 latency <= 200ms など（ソース内定義）

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests streamlit
   （必要に応じてその他パッケージを追加してください）

4. data ディレクトリ作成（プロセス PID / フラグファイル等で使用）
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートの .env / .env.local に設定しておくと自動ロードされます（詳細は kabusys.config）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60  (監視ポーリング間隔 秒)

注意:
- 自動で .env をロードする挙動は kabusys.config により行われますが、テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の有効値: development, paper_trading, live。paper_trading は発注をモックにして DB を分離します。

使い方（主要スクリプト）
- 監視ループ起動（本番想定の監視プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は常に settings.sqlite_path（本番パス）を使用します。

- ExecutionEngine 起動（売買エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
  - 起動時に data/kill.flag が存在すると起動をスキップします。停止は same flag で行えます。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開いて表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（デフォルト: data/paper_trading.db）

- AI / Research 関数の利用例（Python REPL 等）
  - DuckDB 接続を渡して呼び出します（例: ai のニューススコア）
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026,4,1), api_key="sk-...")

    - regime 判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026,4,1), api_key="sk-...")

  - paper_verification_report はコマンドラインツールとして使うのが便利です。

プロセス制御 / 停止
- 実行系プロセスは起動時にプロセス優先度を "high" に設定します（kabusys.utils.process_priority.set_process_priority）。
- 停止はファイルフラグで行います:
  - data/stop_requested.flag: run_monitoring/run_execution の外部停止チェックに使用
  - data/kill.flag: ExecutionEngine を停止させる「安全停止」フラグ（KillSwitch により書き込まれる）
  - data/execution.pid: ExecutionEngine が PID を書き込むファイル（SystemMonitor が存在とプロセス実在を確認）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実装のある場合)
    - broker_factory.py / broker_api.py (実装のある場合)
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
    - paper_verification_report.py
    - __init__.py
  - data/  (実行時に使用される事が多いディレクトリ; リポジトリには含まれない可能性あり)
    - monitoring.db / paper_trading.db / kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid

設定サンプル (.env.example の想定)
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=

注意事項 / 運用上のポイント
- .env の自動ロードは kabusys.config によってプロジェクトルート（.git or pyproject.toml の検出）を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- paper_trading は完全に本番 DB と分離されます。実取引用の資格情報を誤ってテスト DB に流してしまうことがないよう注意してください。
- OpenAI を利用する機能は API 料金が発生します。API キーの管理に注意してください。
- DuckDB に格納される時系列データ・raw_news 等は LLM 処理やリサーチで参照されます。データ鮮度の確認は SystemMonitor により行われます。
- MonitoringDB のスキーマは init_monitoring_db() により冪等に作成・マイグレーションされます。

トラブルシューティング
- SQLite / DuckDB ファイルが見つからない場合は、適切なパスを環境変数で指定するか data ディレクトリを作成してください。
- psutil による優先度設定 / CPU affinity は権限不足で失敗する場合があります（警告ログのみ）。無害な失敗です。
- OpenAI API 呼び出しは 429 / ネットワークエラー / 5xx に対して指数バックオフで再試行する実装です。ただしリトライ上限を超えるとスキップします。

貢献
- バグ修正・改善・テストの追加歓迎です。README に書かれていないコマンドや実行方法がある場合は追記してください。

以上がこのコードベースの概要と主要な使い方です。追加で README に含めたい具体的なコマンドや、環境変数の完全一覧、あるいは運用手順（サービス化 / systemd unit 例など）が必要なら教えてください。