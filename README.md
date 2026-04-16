KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。  
主な役割は以下の通りです。

- 戦略（ファクター計算、特徴量探索）による銘柄選定とポートフォリオ構築
- 注文の発行・管理・リコンシリエーション（ExecutionEngine）
- 監視（システム状態、注文滞留、ドローダウン監視、kill switch、LINE 通知）
- Paper Trading 用の検証レポート生成ツール
- ニュースの NLP による銘柄センチメント評価 / 市場レジーム判定（OpenAI 利用）
- DuckDB / SQLite を利用したデータ処理・永続化

特徴
----
- モジュール化された設計（execution / monitoring / portfolio / research / ai / tools）
- 本番と Paper Trading を分離できる DB パス（PAPER_TRADING_SQLITE_PATH）
- 監視ループと Engine の停止はフラグファイルで安全に制御（data/stop_requested.flag / data/kill.flag）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム判定をサポート（フォールバック・リトライ実装あり）
- Streamlit による監視ダッシュボード（read-only 接続）
- DuckDB を使った高速なファクター計算 / リサーチモジュール

前提・依存
-----------
（実行に必要な主なパッケージ）
- Python 3.9+（typing 機能等を使用）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

セットアップ手順
----------------

1. リポジトリをクローン / ソースを用意
   - この README がプロジェクトルートにある想定（src/ 以下にパッケージあり）。

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit

   （requirements ファイルがあればそれを使ってください:
    pip install -r requirements.txt）

4. PYTHONPATH を通す（パッケージを直接実行する場合）
   - export PYTHONPATH=$(pwd)/src
     （Windows PowerShell: $env:PYTHONPATH = (Resolve-Path .\src).Path）

   代替: パッケージとしてインストール可能であれば pip install -e . を使用。

5. data ディレクトリ作成（初回）
   - mkdir -p data

6. 環境変数の設定
   - .env ファイルをプロジェクトルートに置くことで自動読み込みされます（.env.local で上書き可）。
   - 必須（実行コンポーネントに応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY （AI モジュールを使う場合）
   - 主なオプション:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject  （paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信用）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）

使い方
-----

基本コマンド例（PYTHONPATH=./src を設定している前提）

- ExecutionEngine（売買エンジン）を起動
  - KABUSYS_ENV を切り替えることで paper_trading モードになる（専用 DB を使用）。
  - 実行:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 停止は data/stop_requested.flag を作成すると安全に停止します。
  - 実行時、data/execution.pid に PID を書き込みます（Settings.pid_file_path で変更可）。

- Monitoring（常駐監視プロセス）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 実行:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。
  - 停止は data/stop_requested.flag を作成。

- Streamlit ダッシュボード（read-only）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視 DB を読み込み、ポートフォリオや最新のシステム状態・リスクログを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。
  - 生成される指標: 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ、リスク却下数 など。
  - 設定された閾値を満たすか PASS/FAIL を出力します。

- AI モジュール（プログラムからの呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols の記事を集約し OpenAI で銘柄ごとにセンチメントを算出、ai_scores に書き込む。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルを書き換える。
  - どちらも OPENAI_API_KEY（引数または環境変数）が必要。

運用上の重要点
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring はこのファイルを検出すると安全にループを終了します。外部からの停止シグナルとして使用してください。
- kill.flag（Settings.kill_flag_path）
  - KillSwitch が書くファイル。ExecutionEngine に対する停止要求（例: ドローダウン超過）として用いる設計です。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に完全に分離して記録します。
- プロセス優先度
  - 起動時に set_process_priority("high") が実行されます。必要に応じて環境や権限を確認してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で初期テーブル作成を行い、既存 DB に対して必要なカラム追加（簡単なマイグレーション）も実施します。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュール・ファイルです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリングスクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し・バッチ処理）
      - regime_detector.py           — 市場レジーム判定（MA200 + LLM）
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite 永続化層（monitoring DB）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py             — LINE Push 通知ユーティリティ
      - monitoring_engine.py         — 複数 Monitor の統合ランナー
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - (他、ブローカー抽象・order_repository 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (ランタイムで使用されるディレクトリ: monitoring DB / duckdb / pid / flags 等)

補足: 設定キー一覧（抜粋）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY
- DUCKDB_PATH (default data/kabusys.duckdb)
- SQLITE_PATH (default data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL (環境変数で run_monitoring のループ間隔を上書き)

開発・拡張のヒント
- .env / .env.local により環境変数を管理できます。config.py の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト等で便利）。
- DuckDB 接続を渡す設計のため、研究モジュールは高速に大規模データの計算が可能です。
- OpenAI の呼び出し箇所はテスト時に _call_openai_api をモックすることを想定しており、ユニットテストしやすい構成です。
- 監視やリスク関連はログ記録とデータベース永続化を基本にしているため、外部モニタリングやアラート連携の拡張が容易です。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルート（LICENSE 等）を参照してください。  
- バグ報告・機能要求は Issue を立ててください。

以上が基本的な README です。必要であれば以下を追加で作成します:
- example .env.example（推奨）
- requirements.txt または Poetry / pipenv の設定
- 詳細な運用マニュアル（デプロイ・監視・バックアップ手順）
必要なものを教えてください。