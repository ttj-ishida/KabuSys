KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
主な機能は以下の通りです。

- 注文発行・状態管理を行う ExecutionEngine（ブローカー抽象化対応）
- システム稼働状況 / 注文監視 / リスク監視（Monitoring）
- ポートフォリオ構築（銘柄選定、重み決定、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメント評価 / 市場レジーム判定、OpenAI を使用）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- SQLite / DuckDB を使ったローカル永続化と分析基盤

主な機能一覧
-------------
- Execution
  - 注文作成・送信・同期・リコンシリエーション（Reconciler）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
  - リスク管理（Rate limit, position caps, drawdown など）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視と kill flag 発行
  - AlertManager: LINE へのプッシュ通知（クールダウン管理付き）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り専用で表示）
- Portfolio
  - 銘柄選定（スコア順ソート）、等配分/スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、アグリゲート cap）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL＋Python）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースの銘柄別センチメント評価（OpenAI API をバッチ呼び出し）
  - ETF とマクロニュースを組み合わせた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - 実行 / 監視プロセス起動スクリプト

セットアップ手順
----------------
要件（主なもの）
- Python 3.9+（ソースの typing 等に依存）
- pip

推奨パッケージ（抜粋）
- psutil
- duckdb
- openai
- requests
- streamlit

インストール（例）
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install psutil duckdb openai requests streamlit

（プロジェクト配布に requirements.txt がある場合は pip install -r requirements.txt を使用してください）

環境変数 / .env
- プロジェクトは起動時にプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数を上書きしません。.env.local は上書き）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 重要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD: kabuステーション API 用
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH: 実行管理関連のパス
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

初期ファイル・ディレクトリ
- data/ ディレクトリを作成しておくと便利（PID / flag / DB の格納先）
  - 実行ループは data/stop_requested.flag の存在で自プロセスを終了します
  - kill.flag は監視側が ExecutionEngine に停止を要求するために使用されます

使い方
------
起動スクリプト（簡単な実行例）
- ExecutionEngine（注文エンジン）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を利用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 実行中は data/execution.pid に PID を書き込みます（存在・更新は SystemMonitor でチェックされます）
  - 停止は data/stop_requested.flag を作成するか、実行中プロセスに SIGINT を送ってください

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。値は 1 以上である必要があります。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（paper_trading が選択されていても監視 DB は本番パスを参照します）

- Streamlit ダッシュボード（監視情報の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB のパスを指定可能（既定: data/monitoring.db）。読み取り専用で開きます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
    - または環境変数 PAPER_TRADING_SQLITE_PATH を設定

AI モジュールの利用（プログラムから）
- ニューススコアリング（例）
  - from kabusys.ai import score_news
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")
- レジーム判定（例）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=..., api_key=...)

運用上のフラグ・停止制御
- data/stop_requested.flag
  - run_execution.py/run_monitoring.py のループはこのファイル存在を検知すると安全に終了します（外部から停止させたい場合に使用）。
- data/kill.flag
  - KillSwitch（リスク監視）が条件を満たすと、このファイルを書いて ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側は起動時にこのフラグを検査し、起動を拒否する場合があります。

その他の注意点
- Settings クラスは多数の環境変数をラップしており、不正な値があると ValueError を吐きます（例: KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL など）。
- process priority（psutil） を設定するため、実行時に権限が必要な場合があります。未設定や失敗時はログに警告が出て処理は継続します。
- MonitoringDB（init_monitoring_db）は自動的にテーブル・インデックスを作成／マイグレーションを行います（冪等）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み、Settings オブジェクト
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- tools/
  - paper_verification_report.py
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py 等（注文管理・リコン）
- monitoring/
  - monitoring_db.py (SQLite 永続層)
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, alert_manager.py, kill_switch.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- data/ （実行時に使用する DB / PID / flag を置く想定）
  - monitoring.db（SQLite, 監視ログ）
  - kabusys.duckdb（DuckDB 分析 DB）
  - paper_trading.db（paper_trading 用 SQLite）

開発者向けのメモ
----------------
- DuckDB 接続を受け取って SQL + Python でファクター計算を行う設計です。外部 API 呼び出しは原則分離されています（AI モジュールは OpenAI を使用）。
- テスト時に .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くのモジュールは「副作用なしの純粋関数」を目指しています（特に portfolio/* や research/*）。AI 呼び出し等はリトライ、フォールバックを組み込んでフェイルセーフにしています。

ライセンス / 貢献
----------------
- 現在の配布にはライセンスファイルが同梱されていない場合があります。実運用・配布する際は適切なライセンスを付与してください。
- バグ修正・機能提案は PR／Issue で受け付けてください（リポジトリポリシーに従ってください）。

以上。実運用を行う際は .env を正しく構成し、paper_trading モードでの十分な検証を行ってから live モードへ移行してください。