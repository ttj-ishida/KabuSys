KabuSys — 日本株自動売買システム
================================

これは日本株自動売買システム KabuSys のコードベースです。本 README は開発者向けにプロジェクト概要、提供機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

1. プロジェクト概要
------------------
KabuSys は以下の主要コンポーネントで構成される自動売買フレームワークです。

- 戦略用のファクター計算 / リサーチ（DuckDB ベースの時系列計算）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイジング）
- 注文発行・管理（Broker API 抽象を介した注文送信、状態管理、再コンシリエーション）
- 実行エンジン（ExecutionEngine：ブローカーとのやり取りを行うメイン処理）
- 監視（System / Trade / Risk モニタ、kill switch、LINE アラート、ストリームリットダッシュボード）
- Paper Trading 用の分離された DB と検証用ツール
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント解析）

設計方針の一部：
- DuckDB を用いた歴史データ集計（prices_daily / raw_financials 等）
- SQLite を監視ログ / 注文履歴の永続化に利用
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離
- ルックアヘッドバイアス対策（target_date を引数で渡す等）

2. 主な機能一覧
----------------
- ファクター計算（momentum / volatility / value 等）
- 研究用ユーティリティ（将来リターン、IC、統計サマリ）
- ポートフォリオ構築：候補選定、等配分 / スコア配分、リスク調整（セクター上限・レジーム乗数）
- ポジションサイジング（単元株丸め、aggregate cap、コストバッファ）
- 注文管理：OrderManager、OrderRepository、OrderRecord、再コンシリエーション（Reconciler）
- 実行エンジン起動スクリプト（run_execution.py）
- 監視：SystemMonitor / TradeMonitor / RiskMonitor、MonitoringEngine、kill flag、AlertManager（LINE）
- 監視用ダッシュボード（Streamlit）
- Paper Trading の検証レポート生成ツール（paper_verification_report）
- ニュース NLP（OpenAI）を用いた銘柄ごとのセンチメントスコアリング（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）

3. 必要条件（推奨）
------------------
- Python 3.10+
- 必須 Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード起動時)
  - その他（sqlite3 は標準ライブラリ）
- OS: Linux / macOS / Windows（プロセス優先度関連はプラットフォーム差分あり）

4. セットアップ手順
-------------------
1) リポジトリをクローン
   - git clone ...（プロジェクトルートに .git または pyproject.toml があると .env 自動読み込みが有効化されます）

2) 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3) 必要パッケージのインストール（requirements.txt がある場合はそれに従ってください）
   - pip install duckdb psutil requests openai streamlit

4) 環境変数の設定
   - プロジェクトルートに .env / .env.local を作成して設定できます。自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所があるため環境依存）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の MockBroker の fill 挙動（instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

注意:
- .env のパースはシェル風でクォートや export をある程度サポートします。
- .env の自動読み込みは .git または pyproject.toml をプロジェクトルートとして検出して行います。

5. 実行方法（使い方）
--------------------

基本的にパッケージモジュールとして実行可能なスクリプトが提供されています。

- 監視ループの起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは本番 DB）。

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB (PAPER_TRADING_SQLITE_PATH または data/paper_trading.db) に記録されるため本番 DB と分離されます。
  - 起動時にプロセス優先度を "high" にし、PID ファイルに自身の PID を書く等の起動処理が行われます。

- Streamlit ダッシュボード（監視用）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を read-only で参照します。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / ニューススコアリング（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）と target_date を渡して実行。api_key を指定しない場合は環境変数 OPENAI_API_KEY を使用します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を行い market_regime テーブルに書き込みます。

- 監視・停止シグナル（kill.flag）
  - KillSwitch は条件に応じて kill flag ファイル（デフォルト data/kill.flag）を書き込み、ExecutionEngine 側で検出して安全に停止できます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill.flag をクリアすることができます。

6. 便利な環境変数（要点）
-------------------------
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading では発注実体がモック化され、DB も data/paper_trading.db に分離される。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のファイルパス
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする（"1" で有効）

7. ディレクトリ構成（主要ファイル）
-----------------------------------
以下はソース内の主要モジュールと簡単な説明です（src/kabusys 以下）。

- kabusys/
  - __init__.py
    - パッケージメタ情報（__version__ など）
  - config.py
    - 環境変数の読み込み・Settings クラス（アプリ設定取得）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / paper_trading 切り替え）
  - ai/
    - news_nlp.py: ニュースを OpenAI でセンチメント評価し ai_scores に書き込む
    - regime_detector.py: ETF とマクロニュースを合成して市場レジームを判定
  - data/ (別ファイル群に依存: pipeline / stats 等が想定)
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・スケーリング・単元丸め
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン、IC、統計サマリ等
  - execution/
    - order_manager.py: Order の生成・送信ロジック
    - reconciler.py: 起動時の注文・ポジション突合（自動復旧）
    - （他: broker_factory, execution_engine, order_repository などが存在している想定）
  - monitoring/
    - monitoring_db.py: SQLite 監視ログ DB 初期化と MonitoringDB クラス
    - system_monitor.py: システム・データ鮮度チェック
    - trade_monitor.py: 注文滞留 / 約定異常チェック
    - risk_monitor.py: ドローダウン・ポジション上限の監視
    - kill_switch.py: kill.flag の書き込み（停止シグナル）
    - alert_manager.py: LINE push による通知
    - monitoring_engine.py: 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py: Streamlit 監視ダッシュボード
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成 CLI

8. 運用上の注意
----------------
- Paper Trading と本番 DB は分離してください（KABUSYS_ENV=paper_trading を利用）。
- OpenAI API の呼び出しはレート制限やエラーを考慮してリトライ実装がありますが、API キーとコスト管理に注意してください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存です。権限不足でスキップされる場合があります。
- kill.flag の存在は ExecutionEngine 側で安全停止をトリガーする仕組みです。誤検出を防ぐため KILL_FLAG_CLEAR_ON_START 等で運用ポリシーを整えてください。
- SQLite / DuckDB のパス（data/ 以下）は適宜バックアップ・アクセス制御を行ってください。

9. テスト / 開発
----------------
- 各モジュールは純粋関数として書かれている箇所が多く、ユニットテストが書きやすい設計です（外部API呼び出しはモック可能）。
- OpenAI 呼び出し部分は _call_openai_api を patch してテストできます。
- DB の初期化は init_monitoring_db() で冪等に行えます。

10. 参考コマンドまとめ
---------------------
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースの主要点をまとめたものです。個々のモジュール（特に execution 周りや broker 実装、data pipeline）はそれぞれ詳細な設計と運用上の注意があるため、実稼働前に十分な検証とコードレビューを行ってください。必要であれば各モジュール向けの詳しいドキュメント（設計ノート / API 仕様書）も作成します。