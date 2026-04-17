# KabuSys

日本株自動売買システムの簡易実装サンプル。  
このリポジトリは発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニューススコアリングなどのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注ロジック、ブローカーインタフェース、リスク管理、オーダー管理、再同期（Reconciler）
- Monitoring：システム状態 / 注文状況 / リスク監視、Kill Switch、LINE 通知、Streamlit ダッシュボード
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整
- Research：DuckDB を使ったファクター計算、将来リターン、IC 計算など
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価、レジーム判定
- Tools：Paper Trading 検証レポート生成スクリプトなど
- Utils：プロセス優先度・CPU affinity 設定ユーティリティ等

目的は自動売買パイプラインの構成要素を分離して可視化・テストしやすくすることです。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスクの監視、データ鮮度（prices_daily）チェック、実行プロセスの生存確認
- TradeMonitor：滞留（stale）注文検出、約定価格の異常検出
- RiskMonitor：ドローダウン監視、ポジション数上限監視、ダッシュボード更新、リスクイベント永続化
- KillSwitch：条件に応じて data/kill.flag を書き込みエンジン停止を促す
- AlertManager：LINE Push API による通知（クールダウン管理）
- MonitoringEngine：上記監視を定期ポーリングで実行（本番ループ）
- ExecutionEngine：ブローカークライアントを使った注文送信、RiskManager、OrderManager、Reconciler によるリカバリ
- Portfolio モジュール：候補選定、等重・スコア重み付け、リスクベースのポジションサイズ計算、セクター制約、レジーム乗数
- Research モジュール：モメンタム / ボラティリティ / バリュー等のファクター計算、IC や統計サマリ
- AI モジュール：ニュースの銘柄別センチメントを LLM で評価し ai_scores に書き込み、レジーム判定に LLM を併用
- Streamlit ダッシュボード：監視 DB を読み取りダッシュボード表示
- Tool：paper_verification_report — Paper Trading 用データの検証レポート生成

---

## セットアップ手順

前提：
- Python 3.9+（コードは型アノテーションに Optional | 型記法を使用）
- system パッケージ（sqlite3 は標準）、追加で以下の Python ライブラリが必要です。

推奨インストール（例）:
pip install duckdb psutil requests openai streamlit

（必要に応じて仮想環境を利用してください）

データディレクトリ作成:
mkdir -p data

.env ファイル:
プロジェクトルートに `.env`（または `.env.local`）を作成します。必須・推奨の環境変数は後述します。自動読み込みはデフォルトで有効です（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

DB 初期化:
- 監視用 SQLite（デフォルト）: data/monitoring.db（起動時に必要テーブルが作成されます）
- DuckDB（時系列データ保存）: data/kabusys.duckdb
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

各実行スクリプトを起動すると init_monitoring_db() が呼ばれ DB のテーブル作成や簡易マイグレーションを行います。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（研究モジュール等で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード

任意だが機能に影響:
- OPENAI_API_KEY — OpenAI API キー（AI モジュール、regime_detector 等）
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBroker と専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — Execution エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env を読み込まない

.sample .env（README 用）:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
MONITOR_POLL_INTERVAL=60
LOG_LEVEL=INFO

---

## 使い方（主要コマンド）

リポジトリのルートで Python モジュールとして実行します。

1. 監視ループ起動（Monitoring）
- 監視ループを起動するスクリプト:
  python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止: data/stop_requested.flag を作成するとループは終了します（または Ctrl+C）

注意: Monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（通常 data/monitoring.db）を使用します。

2. Execution エンジン起動
- 実行エンジン起動スクリプト:
  python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録されます（本番 DB と分離）。
- 実行停止: data/stop_requested.flag を作成するか、ExecutionEngine が Kill Switch により停止されると書き込みが行われます。
- PID ファイル: デフォルト data/execution.pid に PID が書かれます。

3. Streamlit ダッシュボード（監視 DB を読み取り）
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで監視 DB にアクセスし、Overview/Positions/Orders/System を表示します。

4. Paper Trading 検証レポート
- 使用例:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  --db /path/to/paper_trading.db
  省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db が使われます。

5. AI / Research モジュールの利用
- ニューススコアリング:
  score_news(conn, target_date, api_key=None) — DuckDB コネクションと target_date を渡して呼び出す（OPENAI_API_KEY 必須）
- レジーム判定:
  score_regime(conn, target_date, api_key=None)

注意: AI モジュールは OpenAI API 呼び出しを行い、429/サーバーエラー等はリトライ処理を行います。テスト時は _call_openai_api をモックできます。

---

## 実行時フラグ / ファイル

- data/stop_requested.flag — run_monitoring / run_execution のループ停止用フラグ
- data/kill.flag（設定可能） — KillSwitch が書き込む停止理由（存在するとエンジン起動を抑止したり停止トリガになる）
- data/execution.pid — 実行中の ExecutionEngine の PID（存在しない/古い PID を検出すると stale として処理）

KillSwitch はリスク条件により kill.flag を作成します。手動でクリアするにはファイルを削除してください。

---

## ディレクトリ構成

リポジトリの主要ファイル（src/kabusys）構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定読み込みロジック
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポートツール
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 監視 DB レイヤ
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, OrderRepository, Reconciler, ExecutionEngine 等の実装)
    - order_manager.py
    - reconciler.py
    - ...
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
  - data/ (推奨されるローカルディレクトリ)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)

（上記は含まれる主なモジュールの要約です。実際のファイルは src/kabusys 以下に展開されています。）

---

## 開発・テスト上の注意

- .env の自動ロードは config.py によりプロジェクトルートを検索して行われます。テストや特殊環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は settings.sqlite_path を常に使用するため、paper_trading と監視 DB を分離したい場合は明示的に SQLITE_PATH を設定してください。
- Paper Trading モードではブローカー呼び出しは Mock 実装にフォールバックし、本番口座にはアクセスしません（DB も分離）。
- OpenAI を使う機能は API キーが必須です。テストでは API 呼び出し関数をモックすることを推奨します。
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。これらのテーブルが整備されていないと Research / AI 機能は動作しません。

---

## 参考（運用ヒント）

- 監視のポーリング間隔は MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックされます。
- プロセス優先度は起動時に set_process_priority("high") が呼ばれます。psutil の権限により実行ユーザが設定できない場合は警告が出ます。
- Kill Switch が作動した際は data/kill.flag に理由が書かれます。自動停止の原因確認と再発防止を行ってからファイルを削除し、再起動してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くため、本番監視が動作中でも安全に参照できます。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実装詳細や API（ブローカーや ExecutionEngine の内部仕様）は各モジュールの docstring を参照してください。必要であれば README を拡張して開発者向けのセットアップ、CI、テスト手順、依存関係の固定（requirements.txt）等を追加できます。