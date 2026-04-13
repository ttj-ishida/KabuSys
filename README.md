KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python パッケージ群です。  
主に以下の役割を持つコンポーネント群を含みます:

- 注文発行・リスク管理・リコンシリエーションを行う Execution（発注エンジン）
- システム健全性、注文滞留、約定異常などを監視する Monitoring
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- ファクター計算・特徴量探索などの Research（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を用いる AI モジュール）
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード等）

機能一覧
--------
主要機能の抜粋:

- Execution
  - Broker クライアント抽象化（paper_trading 時は MockBroker を使用可能）
  - OrderManager による注文状態遷移、送信、再同期（Reconciler）
  - RiskManager によるポジション・利用率等の制限

- Monitoring
  - SystemMonitor: CPU/Memory/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）・約定価格異常検出
  - RiskMonitor: ドローダウン／ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件に基づきファイルを出して ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push を用いたアラート送信（クールダウン実装）
  - Streamlit ベースの監視ダッシュボード

- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC 計算、特徴量統計
  - 候補選定・等重 / スコア重み付け・ポジションサイズ算出・セクター制限 等

- AI
  - news_nlp: ニュース記事を集約して OpenAI でセンチメントを算出し ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースのセンチメントを合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading の SQLite を読み検証レポートを作成
  - monitoring の DB 初期化 / マイグレーションユーティリティ

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上を推奨（型ヒントの表記に対応するため）
   - SQLite（標準ライブラリ）と DuckDB を使用
   - 実行環境に応じて OpenAI API キー、kabu ステーションパスワード等が必要

2. 依存ライブラリのインストール（例）
   pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があればそれを使ってください）
   pip install -r requirements.txt

3. 環境変数 / .env
   プロジェクトルートに .env / .env.local を置くことで環境変数を自動ロードします（OS 環境変数が優先）。  
   自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須で使う場合）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
   - KABUSYS_ENV: 起動環境（development | paper_trading | live） デフォルト: development
   - PAPER_FILL_MODE: paper_trading 時のフィルモード（instant|partial|never|reject）
   - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data 以下）

   注意: config.Settings は .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動でロードします。

使い方
------

基本的な起動例やツール利用法:

- ExecutionEngine を起動（通常運用 / paper_trading 自動判定）
  python -m kabusys.run_execution

  動作:
  - KABUSYS_ENV が paper_trading の場合は paper_sqlite_path（data/paper_trading.db など）を使用し、MockBrokerClient により送受信を模擬します。
  - 起動時にプロセス優先度を "high" に設定し、DB の監視テーブルを初期化します。

- Monitoring の単独ポーリング起動
  MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます。デフォルトは 60 秒。
  python -m kabusys.run_monitoring
  例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  動作:
  - 常に本番の sqlite_path（settings.sqlite_path）を使用して監視ログを保存します（KABUSYS_ENV に関わらず）。
  - 起動時にプロセス優先度を "high" に設定。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --db PATH: SQLite DB ファイルを指定（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）
  出力: 標準出力にレポート（稼働率、注文成功率、レイテンシ等）

- Streamlit ダッシュボード（監視）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュールの利用（プログラムから）
  例: ニューススコア付けを行う
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")

  レジーム判定:
    from kabusys.ai import score_news
    # regime_detector.score_regime() は kabusys.ai.regime_detector に定義されています

- モジュールのプログラム的利用
  パッケージ内の純粋関数（portfolio.*, research.* など）は DuckDB 接続や Python データを渡して呼び出せます。ユニットテストしやすいように DB 参照は最小化されています。

設定のポイント
----------------
- .env のパース
  - コメント、クォート、export KEY=val 形式に対応した柔軟なパーサを採用しています。
  - .env/local の優先度: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト用）。

- データベースの分離
  - 本番監視 DB: settings.sqlite_path（デフォルト data/monitoring.db）
  - Paper Trading: settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - DuckDB: settings.duckdb_path（時系列・ファクタ計算用）

- プロセス制御
  - 起動スクリプトでは set_process_priority("high") を最初に実行します（Windows / POSIX に対応）。
  - CPU affinity を設定するユーティリティも用意されていますが、起動スクリプトは使用していません。

ディレクトリ構成（抜粋）
-----------------------
以下はソースツリー（src/kabusys 以下）の主要ファイル・パッケージ構成です（提供コードに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定読み込み
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py              — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py                — SQLite スキーマ・永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py

運用上の注意
------------
- Paper Trading 時の DB は本番 DB と完全に分離してください（settings.is_paper が自動切り替え）。
- OpenAI API 呼び出しはレート制限や一時エラーに対してバックオフを行いますが、API キーは厳重に管理してください。
- monitoring の polling ループは MONITOR_POLL_INTERVAL に従います。不正な値はデフォルト（60秒）にフォールバックします。
- kill.flag による停止は意図的な安全停止手段です。必要に応じて KILL_FLAG_CLEAR_ON_START を設定してください。
- DB スキーマのマイグレーションは init_monitoring_db() が簡易的に行いますが、本番運用ではバックアップを推奨します。

テスト・開発
-------------
- モジュールは関数単位で分かれており、外部依存（DB・API クライアント）を差し替え可能に実装されています。ユニットテスト時は duckdb の一時 DB や unittest.mock による API 呼び出しの差し替えを推奨します。
- 環境変数自動読み込みを無効にしてテスト用 env を明示的にセットできます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

付録：よく使うコマンド例
-----------------------
- 依存インストール
  pip install duckdb psutil openai requests streamlit

- Execution 起動
  python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
-----
本 README は提供されたソースコードに基づいて作成しています。実際の運用時には各自の環境（API キー、DB パス、運用ルール）に合わせて .env を設定し、事前にテスト環境で動作確認を行ってください。必要であれば README に追記・修正できますので、用途に応じてリクエストしてください。