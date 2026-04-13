README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買/研究/監視用ライブラリ兼実行環境です。  
主な目的は戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、注文発行と実行管理、ならびに実行系と監視系の運用を支援することです。  
このリポジトリには実行（ExecutionEngine）・監視（MonitoringEngine）・AI ベースのニュース/レジーム判定・ポートフォリオ構築ユーティリティ等が含まれます。

主な機能
--------
- Execution
  - ExecutionEngine を通じた注文作成 / 送信 / リコンシリエーション（再起動時の自動同期）
  - OrderManager / OrderRepository による状態管理と DB 永続化
  - Paper trading モード（KABUSYS_ENV=paper_trading）ではモックブローカーと専用 SQLite（data/paper_trading.db）を使用
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/処理プロセスの状態・データ鮮度監視
  - TradeMonitor: 注文滞留（stale orders）や約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - MonitoringEngine: 上記監視をまとめてポーリング、KillSwitch による実行停止（flag ファイル）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio construction
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ算出、セクター集中除外、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - ニュースの NLP スコアリング（OpenAI を用いたセンチメント集約・書き込み）
  - レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシなど）

前提 / 必要環境
---------------
- Python 3.10+
  - 型ヒントに | 演算子や match 等は使っていませんが、Union の省略記法等により 3.10 以上を想定しています
- 必要な Python パッケージ（例）
  - duckdb, psutil, requests, openai, streamlit
  - これらは requirements.txt / pyproject.toml がある場合はそちらを利用してください
- SQLite（組み込み）、ネットワークアクセス（ブローカー API / LINE / OpenAI を使う場合）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone ... (省略)

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - 実際はプロジェクトの pyproject.toml / requirements.txt があればそちらを使ってください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置いて自動ロード可能（config.py による自動読み込み）
   - 主要な環境変数（必須・任意）:
     - 必須（実行する機能に依存）
       - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（strategy/データ系で必要）
       - KABU_API_PASSWORD — kabuステーション API のパスワード（本番接続で必要）
     - OpenAI（AI 機能を使う場合）
       - OPENAI_API_KEY — OpenAI API キー
     - 運用・挙動設定
       - KABUSYS_ENV — 起動環境: development / paper_trading / live （デフォルト: development）
       - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
       - PAPER_FILL_MODE — paper_trading の fill 挙動（instant / partial / never / reject、デフォルト instant）
       - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
       - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
       - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
       - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
       - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
       - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するか（"1" で有効）
       - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
   - .env の書式は shell の export/コメント/クォートにある程度対応しています（config.py の _parse_env_line を参照）。

使い方（起動・コマンド例）
------------------------
- 実行エンジン（本番 / paper_trading）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合は paper_trading DB を使い MockBrokerClient を利用します。
    - 起動時にプロセス優先度を "high" に設定し、DB 初期化（監視用テーブル）を行います。
- 監視ループ（監視プロセス起動）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の monitoring DB）を使用します。
- Streamlit ダッシュボード（ローカルで監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
- AI 機能（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - （これらは DuckDB 接続を受け取り、DB 内の raw_news や prices_daily を参照してスコアを計算・書き込みします。）
- 開発・テスト用
  - MonitoringEngine は MonitoringEngine.run_once() を呼ぶことで単一回のチェックを行えます（ユニットテストで便利）。

重要な挙動・運用注意
-------------------
- KABUSYS_ENV
  - development / paper_trading / live のいずれかを指定します。paper_trading は本番 DB から分離された専用 DB を使用します。
- PID / Kill Flag
  - ExecutionEngine は起動時に PID ファイルを作成します。Monitoring の SystemMonitor は PID を監視し、存在するがプロセスが生きていない（stale PID）場合は削除してアラートを記録します。
  - KillSwitch はリスク条件（ドローダウンやポジション上限）発動時に KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 側でこれを検知して停止する想定です。
- データ鮮度
  - SystemMonitor は DuckDB の prices_daily の最終日付を監視し、最新日からの差分が閾値（_FRESHNESS_DAYS）を超えるとアラート対象にします。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対して軽微なカラム追加（migration）を行います。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                          — 環境変数 / .env 読み込み・Settings クラス
- run_execution.py                   — ExecutionEngine 起動スクリプト
- run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py      — Paper Trading 検証レポート
- ai/
  - __init__.py
  - news_nlp.py                       — ニュース NLP スコアリング（OpenAI 経由）
  - regime_detector.py                — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - __init__.py
  - monitoring_db.py                  — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py                  — LINE Push API 連携
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - (OrderManager, Reconciler, ExecutionEngine, broker_factory 等 — 実行ロジック一式)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - process_priority.py               — プロセス優先度・CPU affinity ユーティリティ
  - __init__.py
- monitoring/ (上に示した monitoring パッケージ)

（上記は主要モジュールの抜粋です。細かなファイルは実際のソースツリーを参照してください。）

サンプル .env（例）
------------------
# KabuSys 基本
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# API / 認証
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
OPENAI_API_KEY=sk-...

# 運用
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
MONITOR_POLL_INTERVAL=60

開発者向けノート
----------------
- DuckDB をローカルに準備し、prices_daily / raw_financials / raw_news 等のテーブルを投入すると、research / ai / regime 機能をローカルで動かせます。
- OpenAI を使う機能は API キーとネットワークアクセスが必要です。失敗時はフォールバック（0.0）やスキップする設計になっていますが、利用時は API レートや課金に注意してください。
- process_priority, cpu_affinity などの操作は OS 権限によって失敗することがあります。該当時は警告ログを出してスキップします。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を記載してください。リポジトリの実ファイルに合わせて追記をお願いします。）

補足
----
この README はコードベースから読み取れる主要な振る舞い・設定をまとめたものです。細かな実装や追加の CLI、設定はソースの docstring / モジュールのコメントを参照してください。必要であれば README にサンプル .env.example や requirements.txt の追加、起動用 systemd ユニット例、Dockerfile などの運用資料を追記できます。