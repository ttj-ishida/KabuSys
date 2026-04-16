# KabuSys — README

このドキュメントはリポジトリ内のコードベース（日本株自動売買システム）についての概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行には各種外部ライブラリ（psutil, duckdb, requests, streamlit, openai など）が必要です。requirements.txt がある場合はそれを利用してください（本リポジトリでは明示されていませんので各モジュールに応じて適宜インストールしてください）。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのモジュール群です。主に以下の機能を備えます。

- 注文管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- モニタリング DB 永続化（SQLite）
- ポートフォリオ構成（候補選定、重み計算、ポジションサイズ決定）
- 研究用モジュール（ファクター計算、特徴量解析）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）とレジーム判定
- Paper Trading 用の分離された DB と検証ツール
- Streamlit ベースの監視ダッシュボード

設計方針として、監視・研究系は本番の発注 API に影響を与えないように分離されており、Paper Trading 環境では発注処理と DB を完全に分離する実装が取り入れられています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアント抽象化（BrokerClientFactory）
  - 注文状態管理、再同期（Reconciler / OrderManager）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch / AlertManager: 異常時に kill.flag を書き出す・LINE通知
  - MonitoringEngine: 監視ループの統合
  - Streamlit ダッシュボードで可視化（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio
  - 候補選定、等重・スコア加重、セクター制限、ポジションサイズ計算
- Research
  - ファクター計算（momentum, value, volatility 等）
  - 将来リターン、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集計と ai_scores 書き込み
  - regime_detector: マクロセンチメント + ETF MA によるレジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## 前提条件

- Python 3.9+
- 必要な外部ライブラリ（例）
  - psutil
  - duckdb
  - requests
  - streamlit
  - openai
  - sqlite3（標準ライブラリ）
- ネットワーク接続（OpenAI 呼び出しや LINE 通知を使う場合）
- .env/.env.local での環境変数管理（任意。src/kabusys/config.py が自動ロードを行います）

インストール例:
- 仮想環境を作成して依存を pip インストールしてください（requirements.txt がある場合はそれを使用）。
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

（requirements.txt がない場合は上記のライブラリを個別に pip install してください）

---

## 環境変数（主要項目）

主な環境変数とデフォルト:

- KABUSYS_ENV: 起動環境 (development, paper_trading, live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知は行わない）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant, partial, never, reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

.env 自動読み込み:
- プロジェクトルートに .env / .env.local が存在すれば自動で読み込まれます（OS 環境変数優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

注意:
- Monitoring は KABUSYS_ENV に関係なく常に sqlite_path（production 想定）を使います。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い本番 DB と分離します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install psutil duckdb requests streamlit openai
   - （ある場合）pip install -r requirements.txt
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定
   - .env.example がある場合はそれを参考にしてください
5. data ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（実行例）

基本的に Python モジュールとして実行します。プロセス優先度設定や DB 初期化は起動スクリプトが自動で行います。

1) Monitoring を起動する（監視ループ）
- 実行:
  - python -m kabusys.run_monitoring
  - 代替: python src/kabusys/run_monitoring.py
- 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト60）
- 停止:
  - プロジェクトルート/data/stop_requested.flag を作成するとループは検知して終了します

2) ExecutionEngine（発注エンジン）を起動する
- 実行:
  - python -m kabusys.run_execution
  - 代替: python src/kabusys/run_execution.py
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると、Broker は Mock を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
- 停止:
  - data/stop_requested.flag を作成すると実行エンジンは停止指示を検出して終了します
  - kill.flag（KILL_FLAG_PATH）を監視している場合、KillSwitch によって書き込まれると起動中の Execution を停止する仕組みがあります

3) Streamlit ダッシュボード（監視 UI）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only で SQLite を開きます（DB が存在しない場合は起動前に MonitoringEngine を実行してください）

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db を上書き）
- 検証指標: 稼働率、注文成功率、送信率、P95 レイテンシなどをまとめて表示します

5) AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- モジュール関数として利用可能:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- これらは DuckDB 接続を受け取り、raw_news / prices_daily 等のテーブルを参照します

---

## 停止・フラグ管理について

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループ監視に用いられます。ファイルが存在すると安全に終了します。
- KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KillSwitch が条件を満たした際に書き込まれるファイル。ExecutionEngine 起動時に clear() しておくオプション等があります。
- PID ファイル（PID_FILE_PATH、デフォルト data/execution.pid）
  - ExecutionEngine の稼働検出に使用。SystemMonitor は stale PID を検出して削除し、risk_log に記録します。

---

## 実装上のポイント / 注意事項

- process priority:
  - 起動スクリプトは最初に set_process_priority("high") を呼んで高優先度を試みます（psutil が必要。権限不足時は警告でスキップ）。
- DB 初期化:
  - init_monitoring_db() により monitoring 用のテーブル（system_status, trade_logs, positions, risk_logs, dashboard 等）を作成します。既存 DB に対しても冪等に動き、必要なカラム追加（マイグレーション）も行います。
- Paper Trading 分離:
  - paper_trading 環境では発注関連データは PAPER_TRADING_SQLITE_PATH に書き込まれ、本番 DB と分離されます。
- OpenAI 呼び出し:
  - レスポンスのバリデーション・リトライ・部分書き込み（コード絞り込み）などフェイルセーフが実装されていますが、API キーや料金には注意してください。
- DuckDB:
  - 大容量の時系列データ（prices_daily, raw_financials 等）を扱うため DuckDB を使用します。conn は各関数に渡して利用します。
- テスト容易性:
  - AI の API 呼び出し部分はラップしてあり、テスト時はモック差し替えがしやすい設計になっています。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要ファイル・ディレクトリ一覧です（抜粋）。実際のツリーはプロジェクトルートに src/ があり、その下がパッケージです。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続層（init + MonitoringDB）
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
    - (その他注文関連モジュール: broker_factory, execution_engine, order_repository...)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                             — 実行時に使用されるデフォルトの DB / flag ファイル群（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）

---

## よくある操作例（まとめ）

- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 付記 / 補足

- この README はコードベースの主要ポイントにフォーカスしています。細かな API や内部ロジック（Engine の設定や Broker 実装、OrderRepository のスキーマ等）は各ソースファイルの docstring / コメントを参照してください。
- 本番運用時にはログレベル、監視間隔、リスク閾値などのチューニングを行い、十分なテストを行ってください。
- OpenAI 等の外部 API を利用する場合は API 使用料や利用規約を確認の上、鍵の管理に注意してください。

---

必要があれば、より詳細な導入手順（例: systemd サービス化、Docker 化、CI 用のテストコマンド、各モジュール API ドキュメント）を追加で作成します。どの部分のドキュメントを拡充したいか指示してください。