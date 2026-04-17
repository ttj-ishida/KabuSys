# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）です。本リポジトリは以下の主要機能を持ち、発注エンジン、監視、ポートフォリオ構築、研究用ファクター計算、ニュース NLP（OpenAI）連携などのコンポーネントで構成されています。

## プロジェクト概要
- 日本株自動売買のコアコンポーネントを含むモジュール群（Execution、Monitoring、Portfolio、Research、AI）。
- SQLite / DuckDB を用いたローカル永続化および分析向けストア。
- Paper Trading（シミュレーション）と Live（本番）を環境で切り替え可能。
- ニュース記事を LLM（OpenAI）でスコアリングしポートフォリオ設計へ活用。
- 監視モジュールはプロセス監視・データ鮮度・注文異常・ドローダウン等を検知し、LINE 経由で通知可能。

## 主な機能（抜粋）
- Execution Engine
  - Broker 抽象化（実ブローカー / MockBroker 切替）。
  - OrderManager / Reconciler による発注と再同期ロジック。
  - RiskManager によるポジション・利用率などの制限。
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度監視。
  - TradeMonitor：滞留注文、約定価格異常監視。
  - RiskMonitor：ドローダウン、ポジション上限監視、ダッシュボード集計。
  - AlertManager：LINE Push 通知（クールダウン管理）。
  - KillSwitch：条件に応じた停止フラグ書き込み（ExecutionEngine 停止）。
  - Streamlit ダッシュボード（監視用 UI）。
- Portfolio
  - 候補選定、等比重・スコア重み、リスクベースの株数決定、セクター上限、レジーム乗数。
- Research
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン、IC 計算、統計サマリ。
- AI
  - news_nlp.score_news：raw_news を LLM で評価し ai_scores テーブルへ書込。
  - regime_detector.score_regime：MA200 とマクロニュースを合成して市場レジーム判定。
- Tools
  - tools.paper_verification_report：Paper Trading DB から検証レポートを生成。

## 前提
- Python 3.10+（typing の | や型注釈に依存）
- DuckDB と sqlite3 を使用
- OpenAI を使う機能は環境変数 OPENAI_API_KEY が必要
- 実ブローカー連携は各自の Broker クライアント設定が必要（KABU_API_PASSWORD 等）

## セットアップ手順（例）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がある想定）
   - pip install -r requirements.txt
   - 必要ライブラリ（抜粋）: duckdb, psutil, requests, streamlit, openai

3. 環境変数を設定
   - .env または .env.local をプロジェクトルートに配置（自動ロードされる）
   - 重要環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV = development | paper_trading | live
     - PAPER_FILL_MODE = instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（分析用 DB、デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を有効にする場合）
     - LOG_LEVEL（DEBUG|INFO|...）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
   - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

4. データディレクトリを作成
   - mkdir -p data

## 起動・使い方

- Execution エンジン（取引エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む
    - 起動時に stop flag (data/stop_requested.flag) があると起動せず終了
    - 実行中に stop flag を作成すると安全に停止する
    - pid ファイルは data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 挙動
    - SystemMonitor（プロセス/データ鮮度）や TradeMonitor / RiskMonitor をポーリング
    - MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（秒）
    - 監視は本番 sqlite_path を環境にかかわらず利用する（Settings.sqlite_path）

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を起動してデータを書き込ませておくこと

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - 例（簡易）:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - または kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

- 停止制御（フラグ）
  - 実行中の Engine / Monitoring を停止するにはプロジェクトルートの data/stop_requested.flag を作成
    - touch data/stop_requested.flag
  - ExecutionEngine を強制終了するための KillSwitch は data/kill.flag を書き込み（自動的に監視が書き込むことが多い）
  - kill.flag を手動でクリアする: rm data/kill.flag

## 設定（Settings）
- Settings クラスは環境変数から設定を読み込みます。
- 主要プロパティ（既定値）:
  - env: KABUSYS_ENV (development | paper_trading | live) — default: development
  - sqlite_path: SQLITE_PATH — default: data/monitoring.db
  - duckdb_path: DUCKDB_PATH — default: data/kabusys.duckdb
  - paper_sqlite_path: PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - pid_file_path: PID_FILE_PATH — default: data/execution.pid
  - kill_flag_path: KILL_FLAG_PATH — default: data/kill.flag
  - PAPER_FILL_MODE: instant | partial | never | reject — default: instant
  - CPU/MEM/DISK 閾値等（監視用）

## 開発者向けメモ
- .env の自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索して決定
  - OS 環境変数が優先（.env は上書きされない。.env.local は上書き可）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Python バージョン:
  - 本コードベースは Python 3.10+（構文や型注釈で | を使用）を想定

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルとインデックスを作成、既存列の追加マイグレーションも含む

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py           — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py    — 市場レジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py      — SQLite 永続化層
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
      - (その他 Broker / Engine / Repository 実装)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py

簡易ツリー（抜粋）
- src/kabusys/
  - run_execution.py
  - run_monitoring.py
  - config.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
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
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

## 注意点 / 運用上のヒント
- Paper Trading は本番 DB と完全分離されるように設計されています（settings.is_paper が有効なときに paper_sqlite_path を使用）。
- 監視は本番 sqlite_path を使用するため、開発環境でも設定次第で本番 DB に書き込まれます。環境変数の設定に注意してください。
- OpenAI API 呼び出しにはレート制限と失敗対策（exponential backoff）が組み込まれていますが、API キー管理やコストに留意してください。
- process priority / CPU affinity の設定は psutil に依存し、実行環境の権限により失敗する場合があります（失敗時は警告ログのみ）。

---

必要であれば、README にサンプル .env.example、requirements.txt の例、より詳細な起動例（systemd ユニットや Dockerfile 例）を追加できます。どの情報を追加したいか教えてください。