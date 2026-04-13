KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコードベースです。本リポジトリは以下の主要機能を持ちます。

- 注文発行・管理（ExecutionEngine / OrderManager）
- リコンシリエーション（再起動後の状態復元）
- 監視（System / Trade / Risk モニタ、アラート、Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- リサーチ（ファクター計算・特徴量探索・IC 計算）
- ニュース NLP（OpenAI を用いたニュースセンチメント）
- レポート・ダッシュボード（Paper Trading 検証レポート、Streamlit ダッシュボード）

本 README はローカル開発 / 実行のための設定・使い方をまとめたものです。

主な機能一覧
--------------
- Execution
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager による注文作成・送信・同期
  - Reconciler による再起動時の自動復旧（OrderSent 照合・ポジション差分検出）
  - Paper Trading モード（MockBroker 使用、専用 SQLite に記録）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: データ/条件に応じて kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（クールダウン機能あり）
  - MonitoringEngine: 上記モニタを束ねてポーリング
  - Streamlit ダッシュボード（監視データ閲覧）
- Portfolio（純粋関数）
  - 候補選定、等重/スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- Research（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を算出
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定
  - 設定管理 (kabusys.config): .env / .env.local の自動ロード（OS 環境が優先）

前提・依存
-----------
主な Python ライブラリ（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを利用する場合）

Python の最小バージョンは型注釈等の利用から 3.10 以上を推奨します。

設定（環境変数）
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（OS 環境が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（名称・説明・デフォルト）:

- KABUSYS_ENV: 起動環境（"development" | "paper_trading" | "live"）。デフォルト: development
  - paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）
- LINE_CHANNEL_ACCESS_TOKEN: LINE push 用 Token（アラート送信）
- LINE_USER_ID: LINE push の送信先 user id
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（"instant" | "partial" | "never" | "reject"、デフォルト: "instant"）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を削除するか（"1" で削除）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートに移動します。
2. 仮想環境を作成して依存をインストールします（例）:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
     （requirements.txt がなければ主要依存を個別インストール: duckdb psutil requests openai streamlit）
3. プロジェクトルートに .env（または .env.local）を作成し、必要な環境変数を設定します。
   - .env.example を参考に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY などを設定してください。
   - OS 環境変数が優先されます。
4. データディレクトリを作成（必要に応じて）:
   - mkdir -p data

注: config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要なエントリポイント）
------------------------------

- 実行エンジン（ExecutionEngine）を起動する
  - 本番（または development）:
    - python -m kabusys.run_execution
  - Paper Trading モード（MockBroker、data/paper_trading.db を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 説明:
    - 起動時にプロセス優先度を "high" に設定し、指定の SQLite / DuckDB に接続します。
    - paper_trading では paper_sqlite_path が使用され、本番 DB と完全分離されます。

- 監視ループを起動する（SystemMonitor の polling）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - 起動時にプロセス優先度を "high" に設定し、monitoring DB（sqlite）と DuckDB に接続します。

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（MonitoringEngine が書き込み中でも閲覧可能）。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（優先順: --db > env PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 機能（プログラム API）
  - ニューススコアを生成:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key を渡すか OPENAI_API_KEY を環境変数で設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime テーブルに書き込みます。

運用時の注意
------------
- Paper Trading と本番 DB は分離されるよう設計されています。KABUSYS_ENV=paper_trading を使用することで paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に切り替わります。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml）を検出して行われます。テスト環境などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Process priority / CPU affinity の設定は psutil を使っています。実行環境によって権限が必要になる場合があります。失敗した場合は警告ログが出て処理は継続します。
- OpenAI 呼び出しはリトライ（指数バックオフ）を行いますが、API キーが無い場合は例外が発生します（関数呼び出し側で必ずチェックしてください）。
- Monitoring の KillSwitch は条件達成時に kill.flag を作成します。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START が "1" の場合にフラグを削除します（設定に応じた起動処理を確認してください）。

ディレクトリ構成
-----------------
（抜粋、主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / .env 管理
    - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュースセンチメント（OpenAI）
      - regime_detector.py          — 市場レジーム判定（ma200 + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py            — SQLite テーブル初期化／永続層
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
      - ...（ブローカー API / order_repository 等の実装が存在）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - process_priority.py

README に含めきれない実装上の詳細
--------------------------------
- 各モジュールには docstring やログが充実しています。実装や挙動の詳細は該当ファイルの docstring を参照してください（特に AI モジュールやポジションサイズ計算、Execution のトランザクション順序などは注意が必要です）。
- DB マイグレーション（monitoring_db.init_monitoring_db）は既存テーブルに列がない場合に追加する処理を含みます（冪等）。

貢献・開発
----------
- ロジックの追加・修正はユニットテストと組み合わせて行ってください。
- .env.example を用意して、必須環境変数の説明を分かりやすく管理してください（本リポジトリに .env.example がある場合はそちらを参照）。

お問い合わせ
------------
実装の意図や使い方で不明点があれば、該当モジュールの docstring を参照のうえ質問してください。README に記載していない内部挙動や設計思想の解説も可能です。