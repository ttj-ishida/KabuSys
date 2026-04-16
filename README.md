# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ兼軽量ランタイム）。  
本リポジトリはトレード実行、監視、リサーチ、ポートフォリオ構築、AI（ニュースセンチメント / レジーム判定）などの機能を含みます。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買に必要な主要機能をモジュール化した Python コードベースです。主な責務は以下です。

- Execution: ブローカー経由の発注、注文管理、リコンシリエーション、リスク管理
- Monitoring: システム稼働監視、注文滞留・約定異常検知、リスク監視（ドローダウン／ポジション上限）、LINE通知、kill-switch
- Research: DuckDB を用いたファクター計算・特徴量探索・将来リターン計算
- Portfolio: 候補選定、重み付け、リスク調整、ポジションサイズ算出
- AI: OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）と市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設計方針の一部:
- DB は SQLite / DuckDB を採用（ローカルファイル）。paper_trading 環境は本番 DB と分離。
- 自動化処理は時刻の参照でルックアヘッドを避ける設計（テスト容易性・バックテスト安全性）。
- 外部 API 呼び出し（OpenAI 等）はリトライ・フェイルセーフを考慮。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（非同期実行スレッドでセッションを回す）
  - OrderManager / OrderRepository / Reconciler による注文状態管理と自動復旧
  - RiskManager による発注制限
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常の検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ作成と LINE 通知
  - MonitoringEngine: 各監視をまとめてポーリング
  - streamlit ダッシュボード（監視 DB を可視化）
- Research
  - ファクター計算（momentum, volatility, value）
  - forward returns, IC（スピアマンランク相関）, ファクター統計
- Portfolio
  - 候補選定、等配分・スコア加重、セクターキャップ適用、リスクベースのサイズ計算
- AI
  - ニュースを集約して OpenAI に投げ、銘柄別センチメントを ai_scores に格納（score_news）
  - マクロニュース＋ETF MA200 乖離から市場レジーム判定（score_regime）
- Tools
  - paper_verification_report: Paper Trading 用の検証レポート出力
  - stop / kill フラグ（data ディレクトリ）で安全停止制御

---

## セットアップ手順

前提:
- Python 3.9+
- git checkout したプロジェクトルートにいることを想定

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は最低限以下を入れてください）
   - pip install duckdb psutil requests openai streamlit

3. data ディレクトリを作成
   - mkdir -p data

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要なキー例:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60
     - LOG_LEVEL=INFO

5. DB 初期化
   - Monitoring / Execution 起動時に必要テーブルは自動で作成されます（init_monitoring_db を参照）。

---

## 使い方（実行例）

※コマンドはプロジェクトルートで実行することを想定します。

- 監視プロセス起動（SystemMonitor をループで回す）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 特記事項:
    - 実行時にプロセス優先度を High に設定しようとします（失敗しても継続）。
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しません）。
    - 停止: data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、paper_sqlite_path に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に data/execution.pid に PID を書きます。data/stop_requested.flag を置くと安全に停止します。
    - kill.flag（Settings.kill_flag_path）を書かれると ExecutionEngine 停止をトリガーできます（KillSwitch 経由）。

- Streamlit ダッシュボード
  - 実行例（監視 DB を読み取り専用で開く）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは直近ダッシュボード値、ポジション、注文、システム状態、リスクログ等を表示します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュールの利用（プログラムから）
  - news_nlp のスコア取得:
    - 例（簡易）:
      - import duckdb
      - from kabusys.ai.news_nlp import score_news
      - conn = duckdb.connect("data/kabusys.duckdb")
      - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - regime 判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - 注意:
    - API キー未設定の場合は例外が出ます。OpenAI API 呼び出しはリトライやフェイルセーフを持ちますが、環境変数 OPENAI_API_KEY の設定を推奨します。

---

## 重要なファイル・フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch が書き込む停止フラグ。ExecutionEngine に停止シグナルを送るために使用します。
- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込むファイル。SystemMonitor はこの PID を参照してプロセスの存否チェックを行います。
- DB
  - data/monitoring.db: 監視ログ（SQLite）
  - data/paper_trading.db: paper_trading 用 SQLite（分離運用）
  - data/kabusys.duckdb: リサーチ用 DuckDB（時系列価格・財務・ニュース等）

---

## 環境設定の自動読み込みについて

- config.py の Settings クラスは起動時に `.env` / `.env.local` をプロジェクトルートから自動読み込みします（OS 環境変数は優先）。
- 自動読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

プロジェクトの主要なディレクトリとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite テーブル定義・永続化ラッパ
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
    - (その他: broker_factory, execution_engine, order_repository, risk_manager 等)
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py

---

## 運用上の注意

- 本番（live）運用時は KABUSYS_ENV=live を設定し、各種キー・パスを適切に保護してください。
- paper_trading モードは本番 DB と完全に分離する設計だが、設定ミスで上書きしないよう .env を慎重に管理してください。
- OpenAI API 呼び出しはコストを伴います。news_nlp / regime_detector の実行頻度は運用ポリシーに合わせて設定してください。
- process priority / cpu affinity 設定は OS 権限に依存します。権限不足でもプロセスは停止しませんがログに警告が出ます。

---

必要があれば README を拡張して、より詳細な実行例（systemd unit ファイル例、Dockerfile、CI のセットアップ、ユニットテストの実行方法など）を追加します。どの部分の情報を追加したいか教えてください。