# KabuSys — README（日本語）

この README は、本リポジトリに含まれる自動売買 / 監視 / リサーチユーティリティ群の概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数と設定
- ファイル・フラグの取り扱い
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムおよび運用支援ツール群です。本パッケージは以下の主要機能を含みます。

- ExecutionEngine（発注処理 / リスク管理 / リコンシリエーション）
- Monitoring（システム状態・注文滞留・リスクの監視、kill switch）
- Portfolio 建設（候補選定、重み付け、ポジションサイジング）
- Research（ファクター計算・特徴量探索）
- AI 支援（ニュースセンチメント：OpenAI を使った NLP 処理、レジーム判定）
- 運用ユーティリティ（paper trading 検証レポート、Streamlit ダッシュボード等）

設計方針として、DuckDB を使ったオフライン分析、SQLite を使った監視ログ保存、OpenAI API を使ったニュース解析を想定しています。Paper trading モードを備え、本番 DB と分離して動作可能です。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine の起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントを抽象化し paper_trading モードでは MockBroker を使用
  - リコンシリエーション（再起動時の注文／ポジション同期）
  - OrderManager、OrderRepository による注文管理

- 監視系
  - SystemMonitor：CPU / メモリ / ディスク使用率、プロセス生存確認、データ鮮度確認
  - TradeMonitor：滞留注文検出、約定価格の異常検出
  - RiskMonitor：ドローダウン・保有数上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch：条件に基づいて data/kill.flag を出力し ExecutionEngine を停止させる
  - AlertManager：LINE Messaging API を使ったプッシュ通知（クールダウン管理）
  - MonitoringEngine：上記を束ねてポーリング実行
  - Streamlit ダッシュボード（監視状況の可視化）

- 研究 / ポートフォリオ構築
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算
  - 候補選定・重み付け・ポジションサイジング、セクターキャップ、レジーム乗数

- AI（OpenAI）
  - news_nlp.score_news：raw_news を要約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime：ETF の MA200 乖離とマクロ記事センチメントを合成し市場レジーム判定

- ツール
  - paper_verification_report：paper trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（typing における | 記法等を使用）
- system によっては psutil のインストールや OpenAI SDK のバージョン差異が必要

インストール（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （リポジトリに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. データディレクトリ作成
   - mkdir -p data

初期設定
- 環境変数は .env / .env.local / OS 環境変数で設定できます。自動読み込みはデフォルトで有効です（プロジェクトルートに .env がある場合）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

デフォルトファイルパス
- monitoring SQLite DB: data/monitoring.db（Settings.sqlite_path）
- paper trading SQLite DB: data/paper_trading.db（Settings.paper_sqlite_path）
- DuckDB: data/kabusys.duckdb
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

## 使い方

以下は主要な起動方法と使い方例です。

1) 監視ループ起動（Monitoring）
- ポーリングで SystemMonitor を回し、監視ログを SQLite に記録します。
- 実行コマンド:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。

2) 実行エンジン起動（ExecutionEngine）
- 発注処理やリスク管理を行うメインエンジンを起動します。
- 本番/ペーパートレード切替:
  - 環境変数 KABUSYS_ENV を `development` / `paper_trading` / `live` のいずれかに設定
  - `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB(data/paper_trading.db) に記録します
- 実行コマンド:
  - python -m kabusys.run_execution

3) Streamlit ダッシュボード（監視 GUI）
- 起動コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で SQLite DB に接続して各種情報を表示します。

4) Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 日付指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 関連
- ニューススコア／レジーム判定は `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` でプログラム的に呼び出せます。
- OpenAI API を使用するため、環境変数 OPENAI_API_KEY を設定してください（api_key 引数で上書き可）。

プロセス管理 / 停止
- run_execution / run_monitoring は起動時にプロセス優先度を上げます（set_process_priority）。
- 実行停止は以下方法を想定:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
  - KillSwitch は条件に応じて data/kill.flag を作成し ExecutionEngine に「停止」シグナルを送ります。
- PID ファイル: run_execution は data/execution.pid を使用します（Settings.pid_file_path により変更可能）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - development / paper_trading / live（デフォルト: development）
  - paper_trading の場合は発注系で MockBroker を使用し、DB を分離

- SQLITE_PATH
  - 監視用 SQLite DB のパス（デフォルト: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite DB のパス（デフォルト: data/paper_trading.db）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔（秒、デフォルト 60）

- PAPER_FILL_MODE
  - paper_trading 時のモック約定挙動（instant / partial / never / reject、デフォルト instant）

- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector が必要）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API トークン（必要に応じて使用）

- KABU_API_PASSWORD, KABU_API_BASE_URL
  - kabuステーション API 用設定

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager による LINE 通知用（未設定時は送信をスキップ）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 をセットすると .env 自動読み込みを無効化

注意: Settings モジュールは .env / .env.local を自動でロードします。必要な必須設定が欠けると起動時にエラーが発生します。

サンプル .env（最低限）
- .env.example に合わせて作成してください。簡易例:
  - KABUSYS_ENV=development
  - OPENAI_API_KEY=sk-...
  - JQUANTS_REFRESH_TOKEN=xxx
  - KABU_API_PASSWORD=secret
  - LINE_CHANNEL_ACCESS_TOKEN=token
  - LINE_USER_ID=Uxxxxxxxxxxxx

---

## ファイル・フラグの取り扱い

- data/stop_requested.flag
  - 存在すると run_monitoring / run_execution のループが終了します（外部から停止するためのフラグ）

- data/execution.pid
  - ExecutionEngine の PID ファイル。SystemMonitor はこの PID を参照してプロセス生存を確認します。

- data/kill.flag
  - KillSwitch が作成する停止指示ファイル。ExecutionEngine 起動時に `kill_flag_clear_on_start` 設定でクリアすることができます。

- SQLite / DuckDB
  - monitoring DB（SQLite）は init_monitoring_db によって必要なテーブルを自動作成・マイグレーションします。
  - DuckDB はリサーチ用 DB として使用されます（prices_daily, raw_financials, raw_news 等のテーブルを想定）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 永続化層（テーブル作成 / DB 操作）
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
    - (その他発注関連モジュール: broker_factory, execution_engine, order_repository, ...)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

その他の補助モジュール（data/、各種 DB 初期データやログ）はリポジトリルートの data ディレクトリを使用します。

---

## 注意事項 / 運用上のヒント

- Paper trading と本番 DB は明確に分離する設計です。KABUSYS_ENV を正しく設定してください。
- OpenAI 呼び出しは API のレートリミットや失敗に対してリトライ実装がありますが、API キーと使用量には注意してください。
- Monitoring は本番 sqlite_path を使用して監視ログを記録します（run_monitoring は KABUSYS_ENV に依存せず本番監視 DB を使用します）。
- process_priority の設定はプラットフォームに依存し、権限不足により変更に失敗する場合があります（警告ログに留められます）。
- DuckDB 操作時は大規模データの読み書きに注意してください。研究用機能はファイルサイズ・メモリ消費を考慮の上実行してください。

---

この README はコードベースから得られる情報を元に作成しています。実運用にあたっては .env.example を参照し、環境変数や依存ライブラリを適切に設定してください。必要であれば、各モジュールのドキュメント（docstring）を参照して詳細な挙動を確認してください。