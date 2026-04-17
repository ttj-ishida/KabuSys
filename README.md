README
=====

概要
----
KabuSys は日本株の自動売買（バックテスト／実運用／ペーパートレード）を想定した小規模な取引システム群です。本リポジトリには、監視（Monitoring）、発注・実行（Execution）、ポートフォリオ構築、ファクター計算、ニュースの NLP スコアリング（OpenAI）など、運用に必要なコンポーネント群が含まれます。

主な設計方針：
- モジュールごとに責務を分離（監視は SQLite、研究は DuckDB、実行は Broker API 経由）
- 環境変数 / .env による設定
- Paper Trading は本番 DB から分離して専用の SQLite を使用
- OpenAI を使った NLP に対してリトライ/フォールバックを実装

機能一覧
--------
- 監視（monitoring）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB 上の prices_daily を参照）
  - 注文滞留／約定異常の検出（trade_monitor）
  - ドローダウン／ポジション上限の監視とリスクイベント記録（risk_monitor）
  - kill.flag による ExecutionEngine の外部停止シグナル（kill_switch）
  - LINE への通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 実行（execution）
  - Broker クライアント抽象と注文管理（OrderManager / OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）および ExecutionEngine（起動・停止の制御）
  - Paper Trading 用の Mock ブローカー（KABUSYS_ENV=paper_trading 時）

- ポートフォリオ構築（portfolio）
  - 候補選定、重み算出（等金額・スコア比率）
  - セクター上限の適用、レジーム乗数
  - 株数計算（単元丸め、利用可能資金に基づくスケーリング）

- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約

- AI（ai）
  - ニュースを OpenAI でスコアリングし ai_scores テーブルへ書き込み
  - マクロニュースと ETF の MA200 を組み合わせた市場レジーム判定（regime_detector）

- ツール
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）

前提条件
--------
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)

インストール（例）
-----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください。）

環境変数 / 設定
----------------
Settings クラスは環境変数（.env / .env.local の自動ロードあり）から設定を取得します。よく使うキー：

必須（実行時に例外となる可能性あり）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／デフォルトあり
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject) デフォルト: instant
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|...）

自動 .env ロード
- プロジェクトルートに .env/.env.local があれば自動で読み込みます（OS 環境変数を上書きしない挙動に注意）。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順
---------------
1. プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に移動
2. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
3. 環境変数を設定（.env を作成するか export で設定）
   - 例 .env（最低限）
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
4. DuckDB / SQLite の初期データについて
   - monitoring DB（data/monitoring.db）は run_monitoring/run_execution 実行時にテーブルが自動作成されます（init_monitoring_db を利用）。
   - research/ai が参照する DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）は別途用意してください（データ投入が必要）。

使い方
------

起動（ExecutionEngine）
- 本番または開発で ExecutionEngine を起動:
  - python -m kabusys.run_execution
- Paper Trading（Mock Broker を使用、DB は data/paper_trading.db）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 停止制御:
  - 実行中にプロジェクトルートの data/stop_requested.flag を作成するとループが検知して安全に終了します。
  - ExecutionEngine 自体は data/execution.pid に PID を書きます。stale な PID を検出すると削除・アラートします。
  - kill.flag（Settings.kill_flag_path）を作ると ExecutionEngine に停止シグナルを送る（KillSwitch 経由）。

起動（Monitoring）
- 監視ループを起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で上書き:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 1秒未満や 0 は無効（デフォルト 60 秒にフォールバック）
- 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使います。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開きます。MonitoringEngine によって DB が更新されていることを確認してください。

Paper Trading 検証レポート
- 単体実行:
  - python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- デフォルトは data/paper_trading.db

AI 関連
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY 必須。未設定時は ValueError を投げます。
- API 呼び出しはリトライとフォールバック（API 失敗時は安全側のデフォルト値）を備えています。

運用メモ
--------
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のメインループが終了します（外部停止）
  - data/kill.flag は実行中の ExecutionEngine を停止させるトリガーとして使用されます（KillSwitch）
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると BrokerClientFactory で MockBrokerClient を作り、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- プロセス優先度:
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼びます。psutil による設定は環境によって権限が必要になる場合があります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対する軽微なカラム追加（例: peak_value, latency_ms）を行います。

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py               — パッケージ宣言 (version)
    config.py                 — 環境変数 / Settings
    run_execution.py          — ExecutionEngine 起動スクリプト
    run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

    ai/
      news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      regime_detector.py      — 市場レジーム判定（MA200 + マクロ NLP）
      __init__.py

    monitoring/
      monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py       — システム・データ鮮度監視
      trade_monitor.py        — 注文滞留・約定異常検出
      risk_monitor.py         — ドローダウン・ポジション上限監視
      kill_switch.py          — kill.flag 書込ロジック
      alert_manager.py        — LINE 送信ユーティリティ
      monitoring_engine.py    — 各 Monitor を束ねる Engine
      streamlit_dashboard.py  — Streamlit ダッシュボード
      __init__.py

    execution/
      order_manager.py        — 注文作成・状態遷移の上位 API
      reconciler.py           — 起動時リコンシリエーション
      ...                     — （Broker, Engine, Repository 等の実装が別ファイルにあります）

    portfolio/
      portfolio_builder.py    — 候補選定・重み計算
      position_sizing.py      — 株数算出・丸め・スケーリング
      risk_adjustment.py      — セクター上限・レジーム乗数
      __init__.py

    research/
      factor_research.py      — ファクター計算（momentum/value/volatility）
      feature_exploration.py  — 将来リターン・IC・統計
      __init__.py

    tools/
      paper_verification_report.py — Paper Trading 検証レポート
      __init__.py

    utils/
      process_priority.py     — プロセス優先度・CPU affinity ヘルパ
      __init__.py

data/
  (実行時に使用する DB / flag / pid ファイルを格納する想定)
  - kabusys.duckdb (DuckDB)
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper trading 用)
  - execution.pid
  - stop_requested.flag
  - kill.flag

貢献・拡張のヒント
-------------------
- DuckDB の prices_daily / raw_financials / raw_news スキーマにデータを投入すると、research / ai 機能が使えるようになります。
- Broker 接続は BrokerClientFactory を拡張して実装してください（実際の kabu API ラッパー等）。
- alert_manager の LINE 以外の通知チャネル（Slack 等）を追加可能です。

ライセンス
---------
（リポジトリにライセンス表記がある場合はそこに従ってください。ここでは明記していません。）

問い合わせ
----------
実行や設定で不明点があれば、主要モジュール（config.py, run_execution.py, run_monitoring.py, monitoring/monitoring_db.py）を参照してください。README の補足が必要なら具体的な要件（実行環境・目的）を教えてください。