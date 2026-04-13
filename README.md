README
======

KabuSys — 日本株自動売買システム
--------------------------------

バージョン: 0.1.0

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアライブラリ群です。  
主に以下の責務を持つモジュールで構成されています。

- 実行エンジン（Execution）: 注文生成・送信・リスク管理・再同期（reconciliation）
- 監視（Monitoring）: システム状態 / 注文・約定監視 / リスク監視 / アラート送信
- ポートフォリオ構築（Portfolio）: 候補選定・重み計算・株数決定・セクター/レジーム調整
- リサーチ（Research）: ファクター計算・将来リターン / IC 計算・特徴量解析
- AI ユーティリティ（AI）: ニュースの NLP スコアリング、レジーム判定（OpenAI）
- ユーティリティ: 環境変数管理、プロセス優先度設定など
- ツール: Paper Trading 検証レポート生成スクリプト、Streamlit ダッシュボード 等

主な設計方針:
- DB（SQLite / DuckDB）を使ったデータ永続化／分析
- 本番と Paper Trading の DB 完全分離（環境変数で切替）
- 外部 API 呼び出し（OpenAI / Broker）に対する堅牢なエラーハンドリングとリトライ
- ルックアヘッドバイアス防止（日時参照の扱いに注意）

機能一覧
--------

- run_monitoring.py: SystemMonitor をポーリング起動（デフォルト 60 秒間隔、環境変数で調整可）
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - データ鮮度チェック（DuckDB の prices_daily）
  - system_status / risk_logs などへの永続化
- run_execution.py: ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録
  - リスク管理、OrderManager、Reconciler の組立てと実行
- monitoring モジュール:
  - MonitoringDB: 監視用 SQLite テーブルの初期化と読み書き（冪等）
  - SystemMonitor / TradeMonitor / RiskMonitor
  - KillSwitch: ファイル (data/kill.flag) による ExecutionEngine 停止シグナル
  - AlertManager: LINE push 通知（クールダウン管理）
  - MonitoringEngine: 各 Monitor を束ねたポーリングエンジン（単発 run_once / ループ run）
  - streamlit_dashboard.py: Streamlit を用いた監視ダッシュボード
- portfolio モジュール:
  - 銘柄選定（select_candidates）、等比率 / スコア加重の重み計算
  - position sizing（risk_based / equal / score）
  - セクターキャップ適用・レジーム乗数
- research モジュール:
  - ファクター計算（momentum / volatility / value）
  - forward returns、IC（Spearman）計算、統計サマリ
- ai モジュール:
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime に書き込む
- tools:
  - paper_verification_report.py: Paper Trading DB（data/paper_trading.db）から検証レポートを生成

必須要件（例）
--------------

- Python 3.10+
- 依存ライブラリ（代表）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準で Python に同梱）
- ネットワーク接続（OpenAI / Broker API 使用時）

セットアップ手順
----------------

1. リポジトリを取得
   - git clone などでプロジェクトルートを取得

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX)
   - .\.venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記必須ライブラリを個別にインストール）

4. 環境変数設定
   - プロジェクトルートの .env または .env.local に必要なキーを設定できます。
   - 自動読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主な環境変数（コード内デフォルト / 必須項目）
- 必須（未設定だと起動時に例外）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（デフォルトあり）:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/…
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視ログ）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag をクリア
  - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定モード、デフォルト instant）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）を使う場合

注意点:
- MONITOR_POLL_INTERVAL: run_monitoring でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=120）。1 以上の整数でなければデフォルト 60 秒にフォールバックします。
- run_execution/run_monitoring はプロセス優先度を "high" にセットしようとします。権限がない場合は警告をログに出力してスキップします。

使い方（代表コマンド）
--------------------

- 監視ループを起動（デフォルトで monitoring 用 SQLite を更新）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading DB（data/paper_trading.db）に記録され、MockBrokerClient が使われます。

- Streamlit ダッシュボード（ローカルで監視結果を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール利用例（Python REPL / スクリプト内）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026,4,1), api_key="sk-...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026,4,1), api_key="sk-...")

- ライブラリ関数（ポートフォリオ / リサーチ等）は通常の Python import で利用できます。
  - 例: from kabusys.portfolio import select_candidates, calc_equal_weights

運用上のポイント / トラブルシュート
---------------------------------
- OpenAI キーが未設定だと ai モジュールは ValueError を投げます。環境変数 OPENAI_API_KEY を設定してください。
- run_execution は起動時に init_monitoring_db を呼び出して監視用テーブルの存在を保証します（冪等）。DB が破損している場合は例外が発生するので DB ファイルのバックアップを取ってください。
- streamlit ダッシュボードはデフォルトで監視 DB を読み取り専用で開きます。起動時に DB が存在しない、または開けない場合はエラーメッセージが表示されます。
- kill.flag（Settings.kill_flag_path = data/kill.flag）が存在すると ExecutionEngine 停止シグナルとして機能します。起動時に自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定（実際の起動スクリプトがクリア処理を呼ぶことを前提）。
- MONITOR_POLL_INTERVAL が 0 や負の値だと警告が出てデフォルト 60 秒が使われます。

ディレクトリ構成（抜粋）
-----------------------

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロードロジック（自動ロード機能あり）
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                        — （ブローカー API / engine 実装等が別ファイルに存在）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py

（上記はリポジトリ内の主要ファイルの抜粋です）

開発メモ / 拡張案
-----------------
- 注文・ブローカー関連の抽象は BrokerAPIProtocol を通じて定義されているため、実ブローカーやモックの差し替えが容易です。
- position_sizing の lot_size は将来的に銘柄別対応（マスタ参照）へ拡張可能。
- news_nlp / regime_detector は OpenAI API を用いるため、料金・レート制限に注意して運用してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）はリサーチ／AI 処理の根幹となるため、データ投入パイプライン（data.pipeline）が別途必要です。

ライセンス・著作権
-----------------
（ここにライセンス情報を追記してください）

最後に
------
この README はコードベースの主要点をまとめたものです。実運用・テスト時は .env.example を整備し、環境変数・データファイルのバックアップを適切に行ってください。質問や追加のドキュメント化希望があればお知らせください。