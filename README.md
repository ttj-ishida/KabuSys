KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買/リサーチ/監視を目的とした小規模なコードベースです。本リポジトリは以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine）と注文管理（OrderManager）
- モニタリング基盤（System / Trade / Risk モニタリング）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、配分、株数決定、セクター制限、レジーム乗数）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 支援機能（ニュースを LLM でスコアリング → ai_scores / 市場レジーム判定）
- 各種ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、検証レポート出力 等）

主な実装方針は「テスト容易性」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のデグレード）」「DB分離（paper_trading と本番）」です。

特徴一覧
---------
- Execution:
  - 本番 / paper_trading を環境変数 KABUSYS_ENV により切替（development / paper_trading / live）。
  - paper_trading 時は MockBrokerClient を使い paper_trading.db に書き込む（本番 DB と完全分離）。
  - 起動時に Reconciler による注文・ポジションの同期処理を行う。

- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク／実行プロセスの PID チェック、データ鮮度チェック（DuckDB）。
  - TradeMonitor: 滞留注文・約定価格の異常検知。
  - RiskMonitor: ドローダウン・ポジション数上限監視、ダッシュボード更新、リスクイベント記録。
  - KillSwitch: サイレントに停止させるための data/kill.flag 書き込み機構。
  - AlertManager: LINE Push API を使った通知（クールダウン管理付き）。

- Portfolio:
  - 候補選定（スコア順）、等金額/スコア重み配分、リスクベースの株数決定、セクターキャップ、レジーム乗数。

- Research:
  - DuckDB の prices_daily / raw_financials を参照して Momentum / Volatility / Value 等のファクターを計算。
  - 特徴量探索（forward returns、IC、統計サマリー）。

- AI:
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）で銘柄別センチメント評価 → ai_scores に保存（バッチ・リトライ・バリデーション実装済）。
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込み。

セットアップ
-----------
前提
- Python 3.10 以上（PEP 604 の union 型等を使用しているため）
- SQLite（Python 標準ライブラリ）および任意に DuckDB（ローカルファイル利用）
- ネットワークアクセス（OpenAI API、LINE API を使う場合）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境とパッケージのインストール
- 仮想環境作成 / 有効化:
  - python -m venv .venv
  - source .venv/bin/activate  (UNIX)
- 必要パッケージをインストール:
  - pip install duckdb psutil openai requests streamlit

環境変数
- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動でロードされます（OS 環境変数優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須（最低限、実行する機能に応じて設定してください）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API（research で必要）
  - KABU_API_PASSWORD — kabuステーション API（Execution の本番接続で必要）
- OpenAI（AI 機能を使う場合）:
  - OPENAI_API_KEY
- LINE（アラート送信を行う場合）:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- その他（主なもの）:
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方
-----

1) 監視ループを起動する（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 動作:
  - Settings から sqlite_path/duckdb_path/pid_file_path 等を読み、MonitoringDB（SQLite）と DuckDB に接続して SystemMonitor をポーリングします。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成すると検知してループを抜けます。

2) 注文実行エンジンを起動する（Execution）
- コマンド:
  - python -m kabusys.run_execution
- 動作:
  - Settings を読み、KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB と MockBrokerClient を使用します（本番 DB と分離）。
  - 実行時に data/execution.pid を使ってプロセスが生きているかを監視します。
  - 同様に data/stop_requested.flag を作成するとエンジン停止処理が開始されます。

3) Streamlit ダッシュボード
- コマンド例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 動作:
  - 監視用 SQLite DB を読み取り専用で接続し、Overview / Positions / Orders / System のタブ表示を提供します。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
- 出力:
  - 稼働率・注文成功率・送信率・レイテンシ等の集約レポートを標準出力に出します。

5) AI 機能（ニューススコアリング / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（raw_news / news_symbols / ai_scores テーブル）を与えて実行します。
  - api_key 未指定時は環境変数 OPENAI_API_KEY を参照します（未設定なら例外）。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB の prices_daily / raw_news を用いて market_regime を算出・書き込みします。

重要なファイル / 動作上の注意
- stop_requested.flag:
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag ファイルの存在を見て安全に停止します。
- kill.flag:
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、実行エンジンに停止を促します（Execution 側はこのフラグの存在で起動を抑制または停止を行います）。
- DB マイグレーション:
  - init_monitoring_db() は冪等にテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）を行います。

ディレクトリ構成（主要部分）
---------------------------
以下は src/kabusys 配下の主要モジュールの抜粋構成です（要約）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込みあり）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート用 CLI
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — Monitoring DB（SQLite）アクセス層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在する想定)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_* (その他関連モジュール)
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
  - data/ (実行時に使用するファイル群を想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag / kill.flag / execution.pid

動作例（簡単なワークフロー）
----------------------------
1. .env を作成して必須環境変数を設定（例: KABUSYS_ENV, SQLITE_PATH, DUCKDB_PATH, OPENAI_API_KEY 等）
2. duckdb ファイルや SQLite DB の初期化（実行スクリプトが init_monitoring_db を呼ぶため、run を始めればテーブルは作られます）
3. 監視プロセスを起動:
   - python -m kabusys.run_monitoring
4. 別プロセスで Execution を起動:
   - python -m kabusys.run_execution
5. 必要に応じて Streamlit ダッシュボードで状況を確認:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
6. 停止するにはプロジェクトルートに data/stop_requested.flag を作成

開発・テスト
------------
- 単体関数群（portfolio / research / monitoring_db の読み書き等）は外部副作用が少なくユニットテストしやすい実装になっています。
- AI / ブローカー呼び出しは外部 API なので、テスト時は該当関数をモック（unittest.mock.patch）して検証してください。
- 設定の自動ロードはテストで邪魔になる場合があるため、 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

ライセンス / 責務
-----------------
- 本 README はコードベースの説明ドキュメントです。商業利用・本番運用時は各外部 API（kabuステーション / OpenAI / LINE 等）の利用規約を確認してください。
- 実際に資金を運用するシステムとして使用する場合は、追加の安全対策、監査、監視、回復手順の整備を強く推奨します（本コードは学習 / PoC 向けの設計思想中心の実装を含みます）。

補足（よく使う環境変数例）
-------------------------
例 .env（テンプレート）
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- MONITOR_POLL_INTERVAL=60

必要に応じてこの README をベースに README.md を追加・拡張してください（例: 開発環境立ち上げ手順、CI 設定、詳細なテーブル定義ドキュメントなど）。