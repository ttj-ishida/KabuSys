# KabuSys

KabuSys は日本株の自動売買システムのコアライブラリ群です。ファクター計算・ポートフォリオ構築・注文管理・実行エンジン・監視・AI ベースのニューススコアリング等、実運用を想定したコンポーネントを含みます。

以下はこのリポジトリの README（日本語）です。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- 銘柄選定・重み付け・ポジションサイジング（Portfolio construction）
- ファクター計算・リサーチ（Momentum / Volatility / Value 等）
- 実行系（Order 管理、Broker クライアント抽象、リコンシリエーション）
- 監視（システム状態・注文滞留・リスク監視、アラート送信、kill switch）
- AI モジュール（ニュースを LLM でスコアリング、マーケットレジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針としては「DB バックエンドは明示的」「ルックアヘッドバイアスを避ける」「外部副作用は明示的に」「フェイルセーフ（API 失敗はデフォルト値にフォールバック）」等を採用しています。

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（スコア降順）
  - 等配分 / スコア加重配分
  - リスク調整（セクター制限、レジーム乗数）
  - 株数決定（risk_based, equal, score）と単元（lot）丸め、aggregate cap
- research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- ai
  - news_nlp: raw_news を LLM（OpenAI）で集約スコアリングして ai_scores に保存
  - regime_detector: ETF (1321) の MA とマクロニュースで日次レジーム判定
- execution
  - OrderManager（状態遷移・重複チェック・送信フロー）
  - Reconciler（起動時の注文・ポジション突合）
  - ExecutionEngine 起動スクリプト（run_execution.py）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite に監視ログを永続化）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - KillSwitch（flag ファイルで実行停止信号を送る）
  - MonitoringEngine（各モニタ束ねてポーリング）
  - Streamlit ダッシュボード（監視情報の可視化）
  - Execution 用監視起動スクリプト（run_monitoring.py）
- tools
  - paper_verification_report.py（Paper Trading の検証レポート生成）

---

## 前提 / 必要環境

- Python 3.10+
  - （型注釈に `|` を使っているため Python 3.10 以上を推奨）
- SQLite（標準ライブラリで利用）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)

例（pip）:
  pip install duckdb psutil requests openai streamlit

※ requirements.txt がない場合は、上記パッケージをプロジェクトに合わせてインストールしてください。

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で行います。自動ロードはデフォルトで有効（プロジェクトルートに .git または pyproject.toml がある場合）。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（使用箇所による）:
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション API）
- OPENAI_API_KEY（AI モジュールを使う場合）

任意 / デフォルト:
- KABUSYS_ENV: 開発モード等（development / paper_trading / live）。デフォルト `development`
  - paper_trading の場合、実行は mock ブローカーを用い、Paper 用 DB に記録されます。
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- DUCKDB_PATH: DuckDB のパス（デフォルト `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルト `data/execution.pid`, `data/kill.flag`）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

監視専用:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。不正値はデフォルトにフォールバックします。

---

## セットアップ手順（ローカルでの例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要なキーを設定します。
   - 例:
       KABUSYS_ENV=development
       SQLITE_PATH=data/monitoring.db
       DUCKDB_PATH=data/kabusys.duckdb
       KABU_API_PASSWORD=...
       OPENAI_API_KEY=...
   - 自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. データディレクトリ作成
   mkdir -p data

6. （Paper Trading を試す場合）`KABUSYS_ENV=paper_trading` を設定すると paper 用 DB に記録されます。

---

## 使い方（起動 / 実行例）

- 実行エンジン（ExecutionEngine）を起動
  - 本番・紙取引は Settings.is_paper / KABUSYS_ENV により分岐します。
  - 例:
      python -m kabusys.run_execution
  - 起動処理:
    - プロセス優先度を high に設定（可能な場合）
    - SQLite / DuckDB に接続（paper_trading の場合は paper_db を使用）
    - Broker クライアント生成 → ExecutionEngine 実行
  - 注意: paper_trading のときは MockBrokerClient が使用され、データは `data/paper_trading.db` に保存されます。

- 監視ループを起動（SystemMonitor 等）
  - 例:
      python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を設定可能（デフォルト 60）。
  - 監視は実行プロセスの PID ファイル確認、DuckDB のデータ鮮度チェック、system_status / risk_logs / trade_logs 等への記録を行います。

- Streamlit ダッシュボード（監視データ可視化）
  - 例:
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視が始まっていること、SQLite DB が存在することが前提です。

- Paper Trading 検証レポート（ツール）
  - 例（デフォルト DB を使う）:
      python -m kabusys.tools.paper_verification_report
    期間指定:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    DB 指定:
      python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等のサマリと PASS/FAIL 判定。

- AI モジュール
  - OpenAI API を使うために `OPENAI_API_KEY` を設定してください。
  - ニューススコアリング:
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1))
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,1))

---

## 運用上の注意

- KABUSYS_ENV が `paper_trading` の場合、発注はモック経由で実行され、本番 DB と分離して `data/paper_trading.db` に保存されます。安全に検証できます。
- 実行時に PID ファイル（デフォルト data/execution.pid）が参照され、存在しない・古い PID は検出・削除されます。kill.flag による停止は KillSwitch で行われます。
- OpenAI 呼び出しはリトライやフォールバックを含みますが、API キーが未設定のときは例外を投げる箇所があります（明示的にエラー通知）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。必要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込みと Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他 broker_factory 等実装がある想定）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

外部データ / 設定ファイル（デフォルト場所）
- data/kabusys.duckdb (DuckDB)
- data/monitoring.db  (監視用 SQLite)
- data/paper_trading.db (paper_trading 用 SQLite)
- data/execution.pid (PID ファイル)
- data/kill.flag (KillSwitch 用フラグファイル)

---

## 開発 / テストに関する補足

- DuckDB はローカルの価格データ・raw_financials・raw_news 等のテーブルを想定します。テスト用に簡易データを投入して動作確認してください。
- モジュールはできるだけ純粋関数（副作用を持たない）で書かれている箇所が多く、ユニットテストを書きやすい設計です。外部 API 呼び出し点は置き換え／モックしやすい構造になっています（例: news_nlp._call_openai_api の置き換え）。
- .env のパースは shell ライクな記法（export、クォート、コメント）をサポートします。

---

必要に応じて README を拡張します。たとえば「Broker クライアントの実装方法」「ExecutionEngine の詳細設定」「DuckDB スキーマ定義」「よくあるトラブルシューティング」などを追加できます。どの内容を優先して追加しますか？