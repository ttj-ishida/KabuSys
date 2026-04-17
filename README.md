# KabuSys

日本株向けの自動売買 / 研究 / 監視フレームワークの小規模実装。  
このリポジトリは注文発行・約定管理、ポートフォリオ構築、モニタリング、AI を用いたニュースセンチメントなどのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 注文管理・ExecutionEngine（発注・リスク管理・リコンシリエーション）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 監視 (System / Trade / Risk) とアラート（LINE プッシュ）
- Paper Trading 用の分離された DB と Mock Broker サポート
- AI モジュール（OpenAI を用いたニュースセンチメント & 市場レジーム判定）
- 研究用モジュール（DuckDB を用いたファクター計算・特徴量解析）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として「本番データへの誤操作を防ぐ」「DBは用途ごとに分離」「外部 API 呼び出しは明示的に設定が必要」等が採用されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション実行・停止）
  - OrderManager（Order State Machine の外向き API）
  - Reconciler（再起動後の自動復旧）
  - ブローカー抽象（Paper Trading 時は MockBroker を使用）
- Portfolio
  - 候補選定（score / rank ベース）
  - 重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（リスクベース、単元丸め、利用可能資金調整）
  - セクター制約・レジーム乗数
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件に応じた停止フラグ生成）
  - AlertManager（LINE push）
  - MonitoringEngine（各 Monitor をまとめてポーリング）
  - SQLite ベースの永続化（monitoring_db）
  - Streamlit ベースの監視ダッシュボード
- AI / Research
  - ニュース NLP（OpenAI を使った銘柄別センチメント -> ai_scores）
  - レジーム判定（ETF MA + マクロセンチメントの合成）
  - ファクター計算、将来リターン、IC、統計サマリ（DuckDB を利用）
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## 必要条件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- （標準ライブラリ）sqlite3, threading, logging 等

※ 実際の開発では requirements.txt / pyproject.toml を用意して pip install してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際は requirements.txt があれば `pip install -r requirements.txt`）

3. データディレクトリ作成（必要に応じて）
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし既存 OS 環境変数は上書きされません）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 必要な環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須のプロパティ参照あり）
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE — paper_trading の埋め方（instant|partial|never|reject） デフォルト: instant
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例（.env）
    JQUANTS_REFRESH_TOKEN=xxxxx
    KABU_API_PASSWORD=secret
    OPENAI_API_KEY=sk-...
    KABUSYS_ENV=development
    PAPER_FILL_MODE=instant
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

---

## 実行方法

各スクリプトはモジュール実行可能（python -m ...）に作られています。

1. 監視ループ起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
   - 監視は KABUSYS_ENV に関わらず常に settings.sqlite_path（通常 data/monitoring.db）を使用します
   - 実行例:
     - python -m kabusys.run_monitoring
   - 停止方法:
     - プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（ファイル存在検知）

2. ExecutionEngine 起動（発注エンジン）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）
   - 実行例:
     - python -m kabusys.run_execution
   - 停止方法:
     - data/stop_requested.flag を作成するとエンジン停止シグナルになります
   - 実行時、実行 PID を data/execution.pid に書き込みます

3. Streamlit ダッシュボード
   - 起動例（監視 DB を読み取りモードで開く）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB に保存された dashboard / positions / trade_logs / system_status / risk_logs を表示します

4. Paper Trading 検証レポート
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション --db で DB パスを指定可能（優先度: --db > 環境変数 > デフォルト data/paper_trading.db）

5. AI / レジーム・ニュース処理（ライブラリ API）
   - ニューススコア付け:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - api_key が省略された場合は環境変数 OPENAI_API_KEY を参照
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意: OpenAI 呼び出しは API キーが必須（未設定時は ValueError）

6. テスト用 / ライブラリ的な使用
   - 研究モジュール（kabusys.research）や portfolio モジュールは DuckDB 接続やメモリデータを渡して利用可能です。

---

## 運用上の注意

- Monitoring は settings.sqlite_path（通常 data/monitoring.db）を使用します。KABUSYS_ENV に関係なく本番監視 DB を参照する設計上の意図があります（監視は環境にかかわらず一元管理）。
- ExecutionEngine は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します（本番 DB と分離）。
- 停止フラグ:
  - data/stop_requested.flag — run_monitoring/run_execution がループ終了判断に使用
  - data/kill.flag — KillSwitch が書き込むことで Execution エンジン停止の合図（KillSwitch は条件を満たすとファイルを書きます）
- PID ファイル:
  - data/execution.pid に ExecutionEngine の PID が書かれます。SystemMonitor はこの PID ファイルを監視し、stale（存在するがプロセスが死んでいる）なら検出して削除します。
- 優先度設定:
  - 起動時に set_process_priority("high") を呼ぶため psutil の権限や OS により設定が失敗する可能性があります（ログに警告）。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py                         # 環境変数 / Settings
    run_monitoring.py                 # Monitoring ポーリングループ起動スクリプト
    run_execution.py                  # ExecutionEngine 起動スクリプト

    execution/
      broker_api.py
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
      order_record.py
      ...                              # 発注周りのコンポーネント

    monitoring/
      __init__.py
      monitoring_db.py                 # SQLite の永続化層 + モデル
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py                 # LINE 通知
      kill_switch.py
      streamlit_dashboard.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py               # DuckDB を使ったファクター計算
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py                      # OpenAI を使ったニュース NLP -> ai_scores
      regime_detector.py               # レジーム判定
      __init__.py

    data/                              # 実行時に使用する data/*.db, flag, pid など（git 管理外想定）
    tools/
      paper_verification_report.py     # Paper Trading 検証レポート
      __init__.py

注: 上記は主要ファイルの抜粋です。詳細はソースコードを参照してください。

---

## 追加情報・開発時のヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。OS 環境変数が優先されます。
- .env.local は .env の上書き（override）用に用意されています（OS 環境変数は保護）。
- MONITOR_POLL_INTERVAL 環境変数で監視の間隔を変更できます（秒、1 以上、デフォルト 60）。
- PAPER_FILL_MODE は paper_trading の MockBrokerClient の挙動を制御します（instant / partial / never / reject）。
- DuckDB は分析・研究用の高速 SQL 処理に使います。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- ローカルで AI 機能を試す際は OPENAI_API_KEY を設定してください。API 呼び出しはレート制限やネットワークエラーを考慮してリトライやフォールバックを行う実装が既に入っていますが、テストでは外部呼び出しをモックすることを推奨します。

---

もし README に追加したいサンプル .env テンプレートや、実行スクリプト（systemd / docker-compose など）の例が必要であれば教えてください。README を運用向けに拡張したテンプレートも作成できます。