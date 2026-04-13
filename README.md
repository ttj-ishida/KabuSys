# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。本リポジトリは以下の主要機能を提供します:

- 注文発行・実行のための ExecutionEngine（ブローカ抽象化）
- 監視（System / Trade / Risk）およびアラート（LINE への Push）
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 調査用ファクター計算・特徴量探索（DuckDB を用いた原始データ処理）
- AI（OpenAI）を使ったニュースセンチメント評価・レジーム判定
- Paper Trading の検証レポート生成、Streamlit ダッシュボード

この README はプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

注意: ソースは src/kabusys 以下にあり、Python 3.10+ を想定しています（型注記に | を使用）。

---

## 主な機能

- Execution
  - ExecutionEngine、OrderManager、Reconciler による発注・状態管理と再起動時リコンシリエーション
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、paper_trading DB に記録して本番 DB と分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringDB（SQLite）へ監視ログの永続化
  - KillSwitch（data/kill.flag）で ExecutionEngine を安全に停止
  - AlertManager による LINE へのプッシュ通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、等配分/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）と研究ユーティリティ（forward returns, IC, summary）
- AI
  - news_nlp: OpenAI API を用いたニュースセンチメント → ai_scores 書き込み
  - regime_detector: MA200 とマクロニュースセンチメントを合成して市場レジーム判定・保存
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード起動スクリプト

---

## 必要条件（概略）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込み）を使用
- （任意）LINE Messaging API トークン、OpenAI API キー などの環境変数

インストール例:
```bash
python -m pip install "duckdb" "psutil" "requests" "openai" "streamlit"
```
※ 実プロジェクトでは requirements.txt を用意してください。

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（Settings モジュール）。OS 環境変数が優先されます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイル。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading）ファイル。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）。デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1" = true）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須、該当機能を使用する場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（Execution に必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知のためのトークン・ユーザーID
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト: 60（0 以下は無視してデフォルトにフォールバック）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト INFO

設定値は Settings クラス（src/kabusys/config.py）で検証されます。

サンプル .env（プロジェクトルート）:
```
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、作業ディレクトリを開く
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
4. 必要な環境変数を .env に設定（プロジェクトルート）。少なくとも Execution を動かす場合は KABU_API_PASSWORD、AI 機能を使う場合は OPENAI_API_KEY を設定。
5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
6. （任意）DuckDB / SQLite データを準備する。研究・バックテストを行うには prices_daily / raw_financials などのテーブルが必要。

---

## 使い方（主要スクリプト）

ここでは開発時に利用する主なモジュールの起動方法を示します。ソースが src/kabusys にあるため、プロジェクトルートで以下のように実行できます。

- 監視ループを起動（MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能、デフォルト 60 秒）
  ```bash
  python -m kabusys.run_monitoring
  # または
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  補足:
  - run_monitoring は Settings で設定される sqlite_path（monitoring DB）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使います。
  - 起動時にプロセス優先度を high に設定しようとします（権限がない場合は警告）。

- ExecutionEngine を起動（本番または Paper Trading）
  ```bash
  python -m kabusys.run_execution
  ```

  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - Execution 起動時は pid_file（デフォルト data/execution.pid）を作成します。KillSwitch は data/kill.flag の存在を確認して停止をトリガーします（必要なら KILL_FLAG_CLEAR_ON_START=1 で起動時にクリア）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

  出力は標準出力にレポートを印字します。PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト DB を上書き可能。

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  監視 DB を read-only で開きダッシュボードを表示します。MonitoringEngine を先に走らせておく必要があります。

- AI 機能（プログラムから呼ぶ例）
  - ニューススコアリング（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）

  どちらも DuckDB 接続を受け取り、OPENAI_API_KEY を環境変数または引数で渡す必要があります。例（簡略）:
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

  注意: API キー未設定時は ValueError が発生します。API 呼び出し時の一時エラーは内部でリトライやフェイルセーフ処理を行います。

---

## 監視関連の重要な挙動

- Monitoring は MonitoringDB（SQLite）へ system_status / trade_logs / positions / risk_logs / dashboard を保存します。init_monitoring_db() は冪等にテーブル作成と簡単なマイグレーションを行います。
- KillSwitch（data/kill.flag）を書き込むことで ExecutionEngine に安全停止シグナルを送ります。KillSwitch は冪等に書き込みを行い、理由文字列をファイルに保存します。
- AlertManager は LINE Push API を用いて通知を送ります。トークン未設定や cooldown 中は送信をスキップしログに記録します。
- SystemMonitor は PID ファイルを確認し、stale PID の検出・除去・ログ化を行います。また DuckDB の prices_daily を参照してデータ鮮度をチェックします。

---

## 開発者向けメモ

- Settings（src/kabusys/config.py）は .env/.env.local を自動ロードします（プロジェクトルートを .git または pyproject.toml で検出）。OS 環境変数を保護するため .env.local の override 挙動が制御されています。
- process_priority ユーティリティは Windows / POSIX の違いを吸収します（psutil に依存）。
- DuckDB を用いる研究モジュールは prices_daily / raw_financials / raw_news 等のテーブル構成を前提とします。テーブル・データの準備は別途行ってください。
- AI モジュールは OpenAI の JSON mode（response_format={"type":"json_object"}）を前提とした実装になっており、レスポンスバリデーションを厳密に行っています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ宣言
- config.py — 環境変数 / 設定読み込みロジック（Settings）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI で銘柄別センチメント算出 → ai_scores 書込み）
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 監視 DB 層（テーブル作成・CRUD）
  - system_monitor.py — システム監視（CPU/MEM/DISK・データ鮮度・PID）
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE 通知管理
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ... — 注文/実行に関するロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算
  - feature_exploration.py — forward returns, IC, summary 等
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/ (想定される出力ディレクトリ)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag

---

## よくある質問（簡易）

- Q: MONITOR_POLL_INTERVAL の最小値は?
  - A: 1 秒以上。環境変数が 0 や負の値、あるいは整数でない場合はデフォルト 60 秒にフォールバックします。

- Q: Paper Trading と本番 DB を混同する心配はありますか？
  - A: run_execution は KABUSYS_ENV が `paper_trading` の場合に PAPER_TRADING_SQLITE_PATH を使用するため、DB は分離されます。ただし Settings の sqlite_path（monitoring 用）は監視系で共通に参照される点に注意してください（monitoring は環境にかかわらず sqlite_path を使用する実装です）。

- Q: OpenAI キーがないとシステムはどうなる？
  - A: AI 機能を呼ぶと ValueError が発生します。AI 関連の処理は（呼び出し元で）キーが無い場合にスキップするよう制御するのが推奨です。

---

この README はコードベース（src/kabusys/*.py）を参照してまとめています。より詳細な設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途ある想定のため、本 README は導入と運用に必要なハイレベルな手引きを提供します。必要であれば各モジュールの API 使用例やテーブルスキーマ説明、運用手順を追加で作成します。