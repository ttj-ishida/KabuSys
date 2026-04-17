# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。本リポジトリは以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築ユーティリティ（選定・重み付け・株数決定・リスク制約）
- リサーチ（ファクター計算・特徴量探索）
- AI 統合（OpenAI を利用したニュースセンチメント / 市場レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- SQLite / DuckDB を用いたデータ永続化

以下にセットアップ方法、使い方、ディレクトリ構成を記載します。

概要
----
KabuSys は主に以下の観点を想定して設計されています。

- 本番・Paper Trading 環境の分離（KABUSYS_ENV）
- 監視コンポーネントによる稼働監視・リスク監視と自動停止シグナル
- DuckDB を使ったリサーチ処理（prices_daily / raw_financials 等を想定）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析やレジーム判定
- 設計はモジュール化（純粋関数／DB 層分離）されておりテストしやすい

主な機能一覧
--------------
- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper DB に記録。
  - Reconciler: 起動時の注文/ポジションの突合せ・自動復旧機能。

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒）。
  - MonitoringEngine: System/Trade/Risk 各 Monitor をまとめてポーリングし、アラートや KillSwitch を実行。
  - AlertManager: LINE Push による通知（設定がある場合）。
  - Streamlit ダッシュボード: monitoring DB を可視化する UI。

- ポートフォリオ構築
  - 銘柄選定（スコア順）、等配分／スコア重み配分、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算（lot 単位で丸め、aggregate cap の補正）等の純粋関数群。

- リサーチ
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）。
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリ。

- AI
  - news_nlp.score_news: raw_news から銘柄ごとにニュースを集約して OpenAI に投げ、ai_scores テーブルへ書き込む。
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースを組み合わせて market_regime に書き込む。

- ツール
  - tools/paper_verification_report.py: Paper Trading DB の指標（稼働率、注文成功率、レイテンシ等）のレポート出力。

前提（Prerequisites）
--------------------
- Python 3.9+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード起動時)
- OS 権限: プロセス優先度設定や psutil による操作では権限が必要な場合があります。

セットアップ手順
---------------
1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合は代表的なパッケージを個別に）
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 必須/主要環境変数（主要なものを抜粋）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要に応じて）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能の利用時）
     - KABUSYS_ENV: 環境名 ("development" | "paper_trading" | "live")。デフォルトは development。
     - PAPER_FILL_MODE: paper_trading 時の fill 挙動 ("instant" | "partial" | "never" | "reject")。デフォルト "instant"
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を使う場合
     - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）

   - 例 (.env):
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=secret
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

5. DB 初期化
   - run_monitoring.py や run_execution.py は起動時に init_monitoring_db() を実行して monitoring DB（SQLite）を作成・マイグレーションします。特別な初期化は不要です。

使い方
------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、MockBrokerClient が使われます。

- 停止方法（ExecutionEngine / Monitoring の安全停止）
  - STOP フラグファイル: data/stop_requested.flag が存在すると run_monitoring/run_execution は終了処理を行います（停止用のフラグ）。
  - KillSwitch（監視側）: リスクが閾値を超えた場合、kill.flag (Settings.kill_flag_path, デフォルト data/kill.flag) を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 実行開始前に kill.flag をクリアしたい場合:
    - from kabusys.monitoring.kill_switch import KillSwitch
      ks = KillSwitch(Path("data/kill.flag")); ks.clear()

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開くため、MonitoringEngine が動いていることが望ましいです。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム呼び出し例）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、api_key を渡して呼び出します。
  - 例:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="sk-...")

注意点／運用上のヒント
--------------------
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定しようとしますが、権限不足だと警告でスキップされます。
- Paper Trading 用 DB は本番 DB と明確に分離されています（設定: KABUSYS_ENV=paper_trading）。
- OpenAI を使う場合はレートリミット／エラーハンドリングが組み込まれていますが、API キー管理・コストに注意してください。
- streamlit を使ったダッシュボードは SQLite を read-only URI で開きます（パスに ?mode=ro を付与）。

ディレクトリ構成
----------------
主要ファイル・モジュールを抜粋して示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 監視 DB レイヤ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository など)
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
    - data/                      — 実行時に使用する data/*.db, flag ファイル 等（リポジトリ外に置く想定）

開発者向けノート
-----------------
- モジュール設計は純粋関数／副作用を最小化する方針で書かれています（テストが書きやすい）。
- DuckDB を用いたリサーチ機能は SQL を中心に高速集計する設計です。prices_daily / raw_financials 等のテーブルスキーマに依存します。
- OpenAI 呼び出し部分はリトライ・レスポンス検証を丁寧に行っていますが、実運用ではプロキシやロギングの強化を検討してください。
- 実行環境の切り替えは KABUSYS_ENV により行います。Paper Trading 時は DB を分離し外部ブローカー呼び出しをモックします。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献ガイドラインを追加してください）

問い合わせ・補足
----------------
使い方で不明点があれば、具体的にどの機能／スクリプトの使い方を知りたいか教えてください。README に具体的なコマンド例や .env.example を追記できます。