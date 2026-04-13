# KabuSys

日本株自動売買システムの一部を抜粋したコードベースの README です。  
この README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リスク管理・監視・リサーチを行うためのモジュール群です。  
このリポジトリに含まれる主な機能群は次の通りです：

- 注文作成・送信・再同期待機能（Execution）
- リスク管理・ドローダウン監視（Monitoring / Risk）
- 監視ログの永続化（SQLite）
- DuckDB を使った価格・ファクター計算（Research）
- ニュースの NLP（OpenAI）を用いたセンチメント評価（AI）
- Paper Trading（モックブローカー、専用 DB）と検証レポート生成ツール
- Streamlit を使った監視ダッシュボード（読み取り専用）

---

## 機能一覧（抜粋）

- Execution
  - 起動スクリプト: `run_execution.py`
  - Broker クライアントの抽象化・ファクトリ
  - OrderManager / OrderRepository / Reconciler（起動時自動リコンシリエーション）
  - RiskManager（ポジション比率・利用率・サーキットブレーカー等）

- Monitoring
  - 起動スクリプト: `run_monitoring.py`
  - SystemMonitor（CPU/メモリ/ディスク、プロセス監視・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション数上限）
  - KillSwitch（フラグファイルで Execution 停止指示）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（複数 Monitor の統合ポーリング）
  - Streamlit ダッシュボード（監視データの可視化）

- Research / Portfolio
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量探索（将来リターン、IC 計算等）
  - ポートフォリオ構成・配分・ポジションサイズ計算

- AI
  - news_nlp: OpenAI を用いたニュースのセンチメント集計と ai_scores への書き込み
  - regime_detector: MA200 とマクロニュースセンチメントを組み合わせた市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法に `X | Y` を使用）
- 必要な主要パッケージ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワーク接続（LINE API / OpenAI を利用する場合）

requirements.txt は本リポジトリに含まれていない想定です。以下例でインストールできます（仮）:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（.env / .env.local をプロジェクトルートに置けます）
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）から自動で `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 主な環境変数（設定とデフォルト）

- アプリケーション環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- API キー等
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能利用時に必須）
  - LINE_CHANNEL_ACCESS_TOKEN（通知を使う場合）
  - LINE_USER_ID（通知を送るユーザ ID）
- DB パス（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- モニタリング関連
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で true）
- ログレベル
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

注意: Settings クラス内の未設定必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は起動時に ValueError を投げます。

.env の読み込みルール:
- OS 環境変数 > .env.local > .env の順で適用。
- .env のパースは独自実装（エクスポート行、引用符、コメントに対応）。

---

## 使い方（代表的なコマンド）

※モジュールはパッケージとして `-m kabusys.xxx` で実行できます。

1. 監視ループ（Monitoring）
   - デフォルトで production 用 sqlite_path を使用して監視テーブルを作成・追記します。
   - 実行:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - または: python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL はポーリング間隔（秒）。不正値または 0 以下はデフォルト 60 秒にフォールバックします。

2. ExecutionEngine（売買エンジン）
   - 本番・ペーパートレード切替:
     - 本番: python -m kabusys.run_execution
     - Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
       - paper_trading の場合は MockBrokerClient を使い、デフォルト db は data/paper_trading.db に分離されます。
   - 注意:
     - 起動時にプロセス優先度（high）を試行的に設定します（失敗しても続行）。

3. Streamlit ダッシュボード（監視データの可視化）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザでダッシュボードを確認できます（読み取り専用で監視 DB を参照）。

4. Paper Trading 検証レポート
   - スクリプト:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
   - オプション:
     - --from YYYY-MM-DD: レポート開始日
     - --to YYYY-MM-DD: レポート終了日
     - --db PATH: SQLite DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH を上書き可能）
   - 出力:
     - 稼働率、注文成功率、送信率、P95 レイテンシなどを標準出力に表示し PASS/FAIL を判定します。

5. AI 機能（ニューススコア / レジーム判定）
   - これらはプログラム的に呼び出す関数として提供されています（サンプル）:
     - from datetime import date
       import duckdb
       from kabusys.ai.news_nlp import score_news
       conn = duckdb.connect("data/kabusys.duckdb")
       score_news(conn, date(2026, 4, 12), api_key="YOUR_OPENAI_KEY")
     - from kabusys.ai.regime_detector import score_regime
       score_regime(conn, date(2026, 4, 12), api_key="YOUR_OPENAI_KEY")
   - 注意:
     - OPENAI_API_KEY を環境変数で設定しておくか、関数に api_key を渡してください。
     - API 呼び出しはリトライ・フォールバックロジックを持っています（失敗時は安全側の値にフォールバックして継続）。

---

## Monitoring DB（SQLite） — 主要テーブル

`init_monitoring_db(conn)` により自動的に作成されるテーブル（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - single row (id=1): portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value, updated_at

これらは MonitoringDB クラスを通して読み書きされます。

---

## ディレクトリ構成（主要ファイル）

以下はソース内の主要ファイルのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他、broker_interface / order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/ (想定)               — データファイル格納場所（duckdb, sqlite 等）

---

## 運用上の注意・実装上のポイント

- 起動時にプロセス優先度を上げようとします（set_process_priority("high")）。権限がないと警告が出てスキップします。
- Monitoring 系は本番の sqlite_path を使って監視データを保存します（環境にかかわらず production DB を参照する設計）。
- Paper Trading は明確に DB を分離します（settings.is_paper 判定で paper_sqlite_path を使用）。
- KillSwitch は flag ファイル（デフォルト data/kill.flag）を作成して ExecutionEngine に停止シグナルを送ります。起動時にクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定する運用も可能。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する書き込み（ai_scores など）は実際のテーブル定義に依存します。AI モジュールは DuckDB 接続を受け取り SQL でデータ取得・書き込みを行います。

---

## 参考コマンドまとめ（例）

- 監視起動（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
- 監視起動（30 秒に変更）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（本番）
  - python -m kabusys.run_execution
- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

以上がこのコードベースの概略 README です。必要であれば、具体的な環境変数のサンプル `.env.example`、requirements.txt、起動用 systemd / supervisor のユニットファイル例、あるいは詳しい DB スキーマドキュメントを追加できます。どれを優先して欲しいか教えてください。