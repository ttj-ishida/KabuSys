# KabuSys

日本株向け自動売買フレームワーク（モジュール群）。  
主な目的は、シグナルの発行・発注・モニタリング・リサーチ・AI によるニュース解析を統合することです。  
この README ではプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は下記の責務を持つ Python パッケージ群です:

- Execution Engine: ブローカーへの発注、リスク管理、注文状態管理、リコンシリエーション
- Monitoring: システム・注文・リスク監視、アラート（LINE）送信、監視 DB 保存
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整
- Research: DuckDB 上でファクター計算や特徴量探索
- AI: OpenAI を用いたニュースセンチメント評価（ai_scores）と市場レジーム判定
- Tools: Paper Trading 検証レポート等のユーティリティスクリプト

設計上、リサーチや AI 処理は実際の発注系（ブローカー API）に影響を与えないよう分離されています。Paper Trading（テスト用）は別 SQLite DB に完全分離されます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注フローを実行
  - Reconciler による起動時リコンシリエーション（注文・ポジション同期）
  - OrderManager / OrderRepository による注文状態管理
- Monitoring
  - SystemMonitor: CPU/MEM/DISK・プロセス存在確認・データ鮮度監視
  - TradeMonitor: 滞留注文（stale）・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - MonitoringEngine: 各モニタを定期実行、KillSwitch 評価、AlertManager 連携
  - AlertManager: LINE Messaging API でのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- AI / データ
  - news_nlp.score_news: OpenAI でニュースを銘柄ごとにスコア化して ai_scores に保存
  - regime_detector.score_regime: MA 乖離＋マクロニュースで市場レジーム判定・保存
  - research.calc_momentum / calc_volatility / calc_value: DuckDB 上でファクター計算
- Portfolio
  - 候補選定、等重・スコア重み、リスクベースのポジション決定、セクターキャップ、レジーム乗数
- Tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL 判定付きの検証レポート生成

---

## セットアップ手順

前提:
- Python 3.9 以上（プロジェクトの型注釈から推奨）
- システムに必要な外部ライブラリ（duckdb, psutil, requests, openai, streamlit 等）

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール（requirements.txt が無い場合は手動で）
   例:
   - pip install duckdb psutil requests openai streamlit
   - （もしテストや開発に必要なら）pip install pytest
4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を用いる（自動ロードされます）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データディレクトリ作成
   - mkdir -p data

推奨パッケージ（最小）:
- duckdb
- psutil
- requests
- openai
- streamlit

---

## 必要な（主要な）環境変数

以下はコードで参照される主要な環境変数の抜粋です（.env に記載しておくと便利です）。

必須（実行内容に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（research で必要）
- KABU_API_PASSWORD — kabuステーション API パスワード（実際のブローカー接続時）

任意・デフォルトあり:
- KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch が書き込むファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

注意:
- Settings クラスは自動的にプロジェクトルートの `.env` / `.env.local` を読み込む（OS 環境変数より優先度が低い）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（主要スクリプト）

プロジェクトはモジュールをスクリプトとして実行できます。いくつかの実行例:

1. Execution Engine の起動（本番/紙/開発は KABUSYS_ENV に依存）
   - python -m kabusys.run_execution
   - 動作:
     - Settings に従い適切な SQLite（paper_trading の場合は paper_sqlite_path）に接続
     - BrokerClientFactory により実際のブローカー or MockBroker を選択
     - ExecutionEngine をスレッドで実行し、data/stop_requested.flag を検知すると停止

2. Monitoring の起動（ポーリングループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
   - 監視は monitoring DB（Settings.sqlite_path）を使用（環境にかかわらず本番パスを参照）

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only URI で SQLite を開き、Positions / Orders / System / Overview を表示

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 範囲指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプションで --db PATH を指定しデータベースファイルを上書き可能
   - 出力は標準出力に要約と PASS/FAIL 判定

5. AI 関連（ライブラリ関数）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡してニューススコアリングを実行（ai_scores テーブルへ書き込み）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 市場レジーム判定を実行し market_regime テーブルへ書き込み

停止用フラグ:
- data/stop_requested.flag: run_execution / run_monitoring はこのファイルを検知すると安全に終了します（起動時は存在しないことが期待されます）。
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを送る用途。KillSwitch.clear() で削除可能。

ログ:
- スクリプトは基本的に logging.basicConfig(level=logging.INFO) を設定して出力します。必要に応じて LOG_LEVEL を設定してください。

---

## ディレクトリ構成（主要ファイルの概観）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージのバージョンとエクスポート設定

- config.py
  - Settings クラス: 環境変数の読み取り、自動 .env ロード、検証ロジック

- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading 用の分離 DB を使用

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト。MONITOR_POLL_INTERVAL を参照

- execution/
  - broker_api.py, broker_factory.py 等（ブローカー関連）
  - execution_engine.py — 発注ループエンジン
  - order_manager.py — 注文状態の API
  - order_repository.py — Orders DB 操作
  - reconciler.py — 起動時自動復旧

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
  - system_monitor.py — CPU/MEM/DISK、プロセス監視、データ鮮度チェック
  - trade_monitor.py — 滞留注文・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — フラグファイル書き込みによる停止シグナル
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各モニタの統合ポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー

- ai/
  - news_nlp.py — raw_news を集約し OpenAI で銘柄ごとのセンチメントを算出、ai_scores に書き込み
  - regime_detector.py — MA200 乖離とマクロセンチメントで市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading DB を解析して検証レポートを出力

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ （実行時に生成される）
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（デフォルト DuckDB）
  - execution.pid / stop_requested.flag / kill.flag などの制御ファイル

---

## 実運用上の注意点 / 既知の実装ポリシー

- Monitoring は Settings.sqlite_path（監視 DB）を使用します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を見に行きます。
- Paper Trading は settings.is_paper=True のとき、paper_sqlite_path に完全分離された DB を使用します（実口座とはデータ分離される）。
- process priority の設定（set_process_priority("high")）は権限が必要な場合があります。失敗すると警告が出てスキップされます。
- OpenAI 呼び出しはネットワークエラー・429・5xx に対して指数バックオフでリトライする実装です。API キーは OPENAI_API_KEY を利用します。
- monitoring_db.init_monitoring_db() は既存 DB に対するスキーママイグレーション（列追加）を試みます。
- .env の自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使っているため、配布後のインストール先構成により自動ロードがスキップされる場合があります。その際は明示的に環境変数を設定してください。

---

## よく使うコマンド例（まとめ）

- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア／レジーム（ライブラリ呼び出し）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

---

README の内容で不明点や補足してほしい箇所があれば教えてください。必要なら .env.example の雛形や systemd / supervisor 向けの起動 unit サンプルなども作成できます。