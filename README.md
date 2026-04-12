# KabuSys — README (日本語)

概要
-----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な内部ライブラリ群です。  
主要コンポーネントは以下のとおりです。

- Execution（ExecutionEngine / OrderManager / Broker クライアント）— 注文作成・送信・リコンシリエーション
- Monitoring（System / Trade / Risk モニタ、アラート、kill-switch、Streamlit ダッシュボード）
- Portfolio（候補選定・重み決定・位置サイズ計算・セクター制限）
- Research（ファクター計算・特徴量探索・IC 解析）
- AI（ニュース NLP によるセンチメント、レジーム判定）
- Tools（Paper Trading の検証レポート等）
- ユーティリティ（設定読み込み、プロセス優先度設定など）

主な機能
---------
- 注文ライフサイクルの管理（作成 → 送信 → 同期 → リコンシリエーション）
- Paper Trading / Live 環境の分離（KABUSYS_ENV）
- 監視ループ（CPU / メモリ / ディスク・プロセス生存確認・データ鮮度チェック）
- リスク監視（ドローダウン検知、ポジション上限監視、リスクイベントログ）
- LINE によるアラート送信（AlertManager）
- Streamlit ベースのリアルタイム監視ダッシュボード
- DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価と市場レジーム判定
- Paper Trading 用検証レポート生成（注文成功率・レイテンシ・稼働率等のサマリ）

前提・依存
-----------
- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（組み込み）
- 環境変数管理は .env / .env.local をサポート（自動ロード。無効化可）

セットアップ手順
----------------
1. Python と依存パッケージをインストール
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - 実際には requirements.txt を用意している場合は:
     - pip install -r requirements.txt

2. プロジェクトルートに .env を作成（または環境変数を設定）
   - 自動ロードはデフォルトで有効（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 必須環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY — OpenAI 呼び出しを行う場合に必要
   - KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
   - 省略時の DB パスなどのデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. データディレクトリを作成（必要に応じて）
   - mkdir -p data

よく使う環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、ExecutionEngine は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使い、MockBrokerClient を使用する設計になっています。
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定挙動 ("instant" | "partial" | "never" | "reject")
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス制御用ファイルパス
- OPENAI_API_KEY: AI モジュール利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）利用時

基本的な使い方
--------------
実行系・監視系・ツールの主要な起動方法は以下のとおりです。プロジェクトルートから実行します。

1. 監視ループを起動（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（デフォルト 60 秒）。
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

2. 実際の ExecutionEngine を起動（注文明細・注文フロー）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録し、MockBrokerClient を使用して本番 DB と分離します。

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で DB を開く実装を行っています（URI に ?mode=ro を付与）。

4. Paper Trading の検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で別 DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と同等）。

5. AI モジュールの利用（プログラム的呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（duckdb.DuckDBPyConnection）を渡してニューススコアを ai_scores テーブルへ書き込みます。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点 / 運用上のポイント
- 実行時にプロセス優先度を "high" に設定するため、set_process_priority() が呼ばれます（psutil を使用）。権限がない場合は警告を出してスキップします。
- Monitoring 用 DB の初期化: init_monitoring_db() が必要テーブルとインデックスを冪等的に作成します（run_monitoring / run_execution 起動時に呼ばれます）。
- Kill Switch は data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。flag の書き込みは冪等です。
- .env 解析は柔軟な実装（クォート・コメント・export 形式をサポート）を備えています。未設定の必須値は Settings の _require() によって起動時に検出されます。
- Paper Trading と Live の DB は分離して運用するよう設計されています（誤操作防止）。

簡単な .env の例
-----------------
（実際の秘密情報は .env に直接コミットしないこと）

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主なファイル・パッケージ（今回提供されたコードベースに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込み
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化層 / MonitoringDB
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
    - (その他 broker / order_repository 等の実装がプロジェクト内に存在)
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
  - data/
    - （DuckDB / SQLite のデータファイルを置く想定ディレクトリ: data/）

開発者向けヒント
----------------
- 型ヒントとドキュメント文字列が豊富に付与されているため、ユニットテストを作成しやすい設計です。外部 API 呼び出し箇所（OpenAI / ブローカー）をモックしてテストしてください。
- DuckDB クエリは SQL の中でウィンドウ関数等を用いているため、大きなデータセットでも効率的に集計できます。ローカル開発時は small subset で動作確認してください。
- ai モジュールは API 呼び出し時のリトライ・バリデーションを備えていますが、API キーやレート制限に注意してください。

ライセンス・貢献
----------------
本リポジトリのライセンス・コントリビューション方針はプロジェクトルートに置かれる LICENSE / CONTRIBUTING.md を参照してください（この抜粋コード内には含まれていません）。

問い合わせ
--------
実装に関する不明点や使い方の質問はリポジトリの issue を立てるか、担当チームのドキュメントに従ってください。

以上がこのコードベースの概要と運用に必要な基本情報です。必要であればセットアップ用の requirements.txt や .env.example、起動ユニットファイル（systemd 例）などのテンプレートも作成できます。どれを優先してほしいか教えてください。