# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。市場データの集計・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、ニュース NLP によるセンチメントなどをモジュール化して提供します。

以下はこのコードベースのREADMEです。

---

## プロジェクト概要

- 目的: 日本株の自動売買ワークフロー（シグナル → ポートフォリオ構築 → 発注 → 監視）を実装するためのモジュール群。
- 特徴:
  - ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約 etc.）
  - 発注エンジン（ExecutionEngine / OrderManager / Reconciler）
  - 監視基盤（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - 研究用途のファクター計算・特徴量解析（DuckDB を用いた処理）
  - ニュースの LLM（OpenAI）によるセンチメント評価と市場レジーム判定
  - Paper Trading 用の分離された DB と検証ツール
  - streamlit ベースの監視ダッシュボード

---

## 機能一覧

- core
  - ポートフォリオ構築: 候補選定、等配分 / スコア配分、リスクベース配分（position sizing）
  - リスク調整: セクター集中制限、レジーム乗数
- execution
  - OrderManager, ExecutionEngine, Reconciler（再起動時の自動復旧）
  - Broker クライアント抽象化（本番 / モックの切替）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: flag ファイルで ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - MonitoringEngine: 複数 Monitor の統合ポーリング
  - streamlit ダッシュボード（監視データの可視化）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ai
  - news_nlp: raw_news をまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA200乖離とマクロニュースを合成して regime ('bull'/'neutral'/'bear') 判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈や X | Y 記法を使用）
- Git, SQLite（組み込み）, DuckDB
- インターネット接続（OpenAI 等外部 API 利用時）

推奨パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

例: 仮想環境作成とインストール
- Unix 系:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil requests openai streamlit

データディレクトリ作成
- プロジェクトルートに `data/` ディレクトリを作成してください（PID / DB / flag ファイルをここに置きます）。
  - mkdir -p data

.env の自動読み込み
- デフォルトでプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先されます）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境を指定。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API 用パスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、paper 専用の SQLite を使用します。

---

## 使い方

起動・実行の代表例

1. ExecutionEngine を起動（実際に発注を行うコンポーネント）
- 通常:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper 環境では MockBrokerClient を使用し、paper DB（デフォルト data/paper_trading.db）へ記録されます。

2. Monitoring（監視ループ）を起動
- python -m kabusys.run_monitoring
- オプション: ポーリング間隔を変更する場合は環境変数 MONITOR_POLL_INTERVAL を秒数で指定（デフォルト 60）
  - export MONITOR_POLL_INTERVAL=30

監視と停止
- ExecutionEngine の停止は kill.flag（デフォルト: data/kill.flag）を作成することで実行できます（KillSwitch が検知すると停止します）。KillSwitch はデフォルトで drawdown や position limit トリガーで書き込みます。
- 手動で停止させたい場合は `data/stop_requested.flag` を作成すると run_* スクリプトが検知して終了します（run_monitoring.py / run_execution.py で使用）。
- kill.flag のクリア:
  - rm data/kill.flag
  - または KillSwitch.clear() を呼ぶ管理ツールを実装して利用可能。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- streamlit ダッシュボード（監視データの可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

AI モジュール利用
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を渡す必要あり。
- regime_detector.score_regime(conn, target_date, api_key=None)

注意事項（運用上のポイント）
- run_monitoring は常に「本番用の sqlite_path」を使って監視データを書きます。KABUSYS_ENV に依存せず本番の monitoring DB を使う設計です（監視のみを分離していない場合は注意）。
- Execution の paper_trading は発注先をモックするため、必ず paper 用 DB に記録されます。
- 実行前に .env（.env.example 参照）で必須変数を設定してください。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定読み込みロジック
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - data/                          — データ処理モジュール（別ツリー、ここでは参照）
    - execution/
      - broker_api.py                — Broker API 抽象
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - order_record.py
    - monitoring/
      - monitoring_db.py             — monitoring DB スキーマ + ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - process_priority.py

- data/    — 実行時に使うファイル群（DB / PID / flag 等）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 主要な DB / スキーマ情報（監視関連）

監視用 SQLite（init_monitoring_db により自動作成）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の単一行で集計情報保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

マイグレーション:
- 既存 DB に足りないカラム（peak_value、latency_ms）は init_monitoring_db 実行時に追記されます（冪等性あり）。

---

## 開発上のヒント

- ログレベルは環境変数 LOG_LEVEL で制御できます（Settings.log_level）。
- `.env` / `.env.local` の読み込みは config.py が自動で行います（OS環境変数優先）。テストで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- プロセス優先度や CPU affinity を設定するユーティリティがあります（kabusys.utils.process_priority）。
- AI（OpenAI）呼び出し箇所はリトライやフォールバック（失敗時 0.0 等）を組み込んであるため、API 失敗時もシステム全体が壊れない設計です。

---

## よく使うコマンドまとめ

- 仮想環境作成 & パッケージインストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- Execution 起動（Paper / Live）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 報告書生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースに含まれるモジュールの挙動と典型的な使い方をまとめたものです。運用時は .env の設定や DB のバックアップ、OpenAI/API キー管理、監視アラート先（LINE）の設定を適切に行ってください。