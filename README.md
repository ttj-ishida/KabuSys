# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。価格データの集計（DuckDB）、Order 発行および Reconciliation、監視ダッシュボード、Paper Trading 検証ツール、LLM を用いたニュース NLP / レジーム判定などの機能を含みます。

---

## 概要

このリポジトリは以下の機能群を提供します。

- 自動売買の実行エンジン（ExecutionEngine）と関連コンポーネント（OrderManager, RiskManager, Reconciler など）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と監視DB
- 監視ダッシュボード（Streamlit）
- Paper Trading 用の検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイジング、セクター制約）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI 関連機能：ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- 一部ユーティリティ（プロセス優先度設定、設定ロード）

重要な設計方針の例:
- 環境（KABUSYS_ENV）に応じた挙動（paper_trading は DB を分離）
- ルックアヘッド（date.today() 等）の防止を意識した実装
- フェイルセーフ（API 失敗時はデフォルト値で継続など）

---

## 主な機能一覧

- Execution
  - Order 作成・送信・同期（OrderManager）
  - ブローカー API 抽象 → BrokerClientFactory で Mock / 実装を切替え
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて flag ファイルを書き ExecutionEngine を停止させる
  - AlertManager: LINE によるプッシュ通知（クールダウン制御）
  - MonitoringEngine: 上記を束ねたポーリングエンジン
  - Streamlit ダッシュボード（監視 DB を参照）

- Research / Portfolio
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - ファクターの特徴量探索・IC 計算
  - ポートフォリオ候補選定・重み計算・ポジションサイジング・セクター制約

- AI
  - news_nlp.score_news: raw_news を OpenAI に送り銘柄別センチメントを取得、ai_scores に保存
  - regime_detector.score_regime: ETF MA 乖離 + マクロニュースを LLM で評価して market_regime に格納

- Tools
  - paper_verification_report: Paper Trading DB を解析して合格/不合格判定レポートを出力

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（コードは typing の構文等を使用）
- システムに sqlite3 が使えること
- DuckDB（Python パッケージ）を用いるため、pip インストールが必要

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - (mac/linux) source .venv/bin/activate
   - (windows) .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトで requirements.txt を用意していれば pip install -r requirements.txt）

4. データディレクトリの作成
   - mkdir -p data

5. 環境変数 / .env を準備
   - プロジェクトルートに .env（または .env.local）を置くことで自動ロードされます（config.py の自動読み込み）。
   - 重要な環境変数の例:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（監視DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）
     - PID_FILE_PATH / KILL_FLAG_PATH（デフォルトは data/execution.pid / data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループ間隔を秒で上書き、デフォルト 60）

   - .env のサンプルの書き方:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=paper_trading

注意:
- config.py は OS 環境変数を優先して .env を読み込みます。テストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要コマンド）

- 監視ループを起動（Monitoring）
  - 環境変数でポーリング間隔を上書き可:
    - export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作:
    - Settings に基づく sqlite (監視 DB) と DuckDB へ接続し、SystemMonitor を定期実行します。
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path を使用します（監視は本番 DB を参照する想定）。

- 実行エンジンを起動（Execution）
  - paper_trading モードでは MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - BrokerClientFactory でブローカークライアントを決定し、ExecutionEngine を用いてセッションを実行します。
    - 起動時に pid_file を書き、終了時にクリーンアップします。

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

- Paper Trading 検証レポート
  - 起動:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db data/paper_trading.db

- AI スコアリング / レジーム判定（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数で渡すか OPENAI_API_KEY 環境変数）

---

## 設定（主な環境変数 / Defaults）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う場合
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine PID ファイル）
- KILL_FLAG_PATH: data/kill.flag（KillSwitch 用）
- KILL_FLAG_CLEAR_ON_START: "1" にすると Execution 起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒） default: 60

config.py 内にバリデーション・デフォルト値の記述があります。必須の値が未設定の場合、Settings プロパティアクセス時に ValueError が発生します。

---

## 動作上の注意点 / 実装メモ

- Monitoring DB の初期化:
  - init_monitoring_db(conn) は冪等にテーブルとインデックスを作成します。既存 DB に対してカラム追加（migrations）も簡易に行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- KillSwitch:
  - RiskMonitor が閾値超過などを検出すると kill.flag を書き込み、ExecutionEngine に対して停止指示を与えます。flag は既存なら再書き込みせず冪等挙動。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（paper_trading.db）を使用し、本番 DB と完全分離します。
- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます。psutil により Windows / POSIX の差分を吸収します。権限不足時は警告ログを出して継続します。
- LLM 呼び出し:
  - OpenAI API 呼び出しはリトライ（429, network, timeout, 5xx）を実装。失敗時はフェイルセーフ動作（0.0 でフォールバックやスキップ）を行います。
- DuckDB / SQLite:
  - リサーチ系は DuckDB（prices_daily, raw_financials 等）を参照。監視やトレードログは SQLite（monitoring.db / paper_trading.db）で管理。
- 時刻・タイムゾーン:
  - DB へは ISO8601 UTC を用いて記録します。ニュース窓等は JST/UTC の変換を明示的に行います。

---

## ディレクトリ構成（主要ファイル）

（src 以下を参照）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定ロード
  - run_monitoring.py                   — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record, risk_manager など)
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
  - tools/
    - __init__.py
    - paper_verification_report.py
  - (その他: data パッケージ等は別ファイル群として参照)

注: 上記はリポジトリ内の主要モジュールを抜粋したものです。細かな補助モジュール（data.pipeline, data.stats, execution.broker_api 等）も存在します。

---

## よくある質問

Q: 監視はどの DB を使いますか？  
A: Monitoring（run_monitoring）は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。KABUSYS_ENV に依らず同一の sqlite_path を使用する設計です。

Q: Paper Trading と本番 DB は分離されていますか？  
A: はい。KABUSYS_ENV=paper_trading のとき、run_execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。

Q: MONITOR_POLL_INTERVAL の値が不正なときは？  
A: integer で 1 以上を期待します。無効値や 0 以下の場合は警告ログを出しデフォルト（60秒）へフォールバックします。

Q: OpenAI API キーが未設定のときは？  
A: AI 機能を呼び出すと ValueError を投げます。API を使わない限りは影響しません。テスト時は API 呼び出し関数をモックできます（モジュール内で呼び出し分離済み）。

---

もし README に追加したい例（.env.example のテンプレート、systemd ユニットファイル例、Dockerfile、CI 設定等）があれば、その内容に合わせて README を拡張します。