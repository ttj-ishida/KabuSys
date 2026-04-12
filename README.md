KabuSys — README (日本語)
========================

概要
----
KabuSys は日本株向けの自動売買 / 監視 / リサーチ用モジュール群です。本リポジトリは以下の主要機能を持ち、実運用を念頭に設計されています。

- 注文発行・状態管理とブローカー連携（実口座 / ペーパートレード分離）
- リコンシリエーション（起動時の自動復旧）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイジング）
- ファクター計算・特徴量探索（DuckDB を用いたオンチェーン計算）
- ニュース NLP によるセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 監視基盤：システム状態・注文異常・リスク監視、LINE 通知、Streamlit ダッシュボード
- ツール: ペーパートレード検証レポート生成スクリプト 等

主な特徴
--------
- 環境ごとの挙動切替（KABUSYS_ENV: development | paper_trading | live）
  - paper_trading では MockBrokerClient を使用し、paper 用 SQLite（data/paper_trading.db）に記録。
- DuckDB を用いたファクター / 研究処理（prices_daily / raw_financials などを前提）
- OpenAI を使ったニュース評価（gpt-4o-mini を想定）と市場レジーム判定
- 監視コンポーネントは SQLite（monitoring DB）にログを永続化し、Streamlit で可視化
- 実行プロセスは起動時にプロセス優先度を設定（psutil 経由）してリソース管理

セットアップ
-----------
1. Python 環境準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit

   実際のプロジェクトでは requirements.txt / poetry 等で管理してください。

3. データディレクトリ作成（必要に応じて）
   - mkdir -p data

4. 環境変数（.env ファイル推奨）
   プロジェクトはルートの .env / .env.local を自動読込します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込を無効化可）。
   主要な環境変数（デフォルト / 備考を併記）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須 / J-Quants API 用トークン）
   - KABU_API_PASSWORD: （必須 / kabuステーション API のパスワード）
   - OPENAI_API_KEY:（OpenAI API キー。ai モジュールを使う場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID:（アラート送信に使用）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（監視ログ用、デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper の約定挙動、デフォルト: instant）
   - PID_FILE_PATH: data/execution.pid（ExecutionEngine 用 PID ファイル）
   - KILL_FLAG_PATH: data/kill.flag（ExecutionEngine 停止フラグ）
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）
   - LOG_LEVEL（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照。デフォルト 60）

使い方（主な実行例）
-------------------

- 監視ループ起動（SystemMonitor 単体の永続ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL を使って間隔を変更可能（デフォルト 60 秒）
  - 実行:
    - python -m kabusys.run_monitoring
  - 挙動:
    - PID/kill フラグ、DuckDB/SQLite へ接続して system_status / risk_logs などを記録

- ExecutionEngine 起動（実運用 / ペーパートレード）
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録
  - 実行:
    - python -m kabusys.run_execution
  - 起動時に Reconciler を実行して未確定注文の同期、ポジション差分チェックを行う

- Streamlit ダッシュボード
  - 監視 DB を読み取り専用で表示します（MonitoringEngine を先に動かすことを推奨）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パス指定:
      - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI / Research API の呼び出し（プログラムから）
  - ai:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, date(2026,4,1), api_key="...")
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, date(2026,4,1), api_key="...")

設定・運用上の注意
-----------------
- .env 読み込み:
  - プロジェクトルートの .env / .env.local を自動読み込みします（CWD ではなくファイル位置からプロジェクトルートを探索）。
  - 自動読み込みを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB 初期化:
  - monitoring 用 SQLite は init_monitoring_db() により必要テーブルを作成／マイグレーションします（冪等）。

- ペーパートレード分離:
  - KABUSYS_ENV=paper_trading に設定すると実ブローカー API を使わずモックを使用し、DBも paper_trading 用ファイルに分離されます（安全）。

- OpenAI 呼び出し:
  - API 呼び出しはリトライ（指数バックオフ）等の実装がされていますが、API キーの設定（OPENAI_API_KEY）は必須です。
  - レスポンスのバリデーション処理や部分書込み（部分失敗時に既存データ保護）も実装されています。

ディレクトリ構成（抜粋）
----------------------
以下は主要なファイル / モジュールのツリー（src/kabusys 以下の抜粋）です。実際のリポジトリにはさらにファイルが存在する可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                      (環境変数/設定管理)
    - run_monitoring.py              (SystemMonitor ポーリング起動スクリプト)
    - run_execution.py               (ExecutionEngine 起動スクリプト)
    - tools/
      - __init__.py
      - paper_verification_report.py (Paper Trading 検証レポート)
    - ai/
      - __init__.py
      - news_nlp.py                  (ニュース NLP スコアリング)
      - regime_detector.py           (市場レジーム判定)
    - monitoring/
      - __init__.py
      - monitoring_db.py             (SQLite 永続化層)
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - (その他: broker_factory, execution_engine, order_repository 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py

補足: 主なクラス / 関数の説明
---------------------------
- Settings (kabusys.config)
  - 環境変数を読み取り、デフォルトや検証を行う central 設定オブジェクト
- MonitoringDB (kabusys.monitoring.monitoring_db)
  - system_status / trade_logs / positions / risk_logs / dashboard の読み書き API
- SystemMonitor / TradeMonitor / RiskMonitor
  - それぞれシステム状態、注文の滞留や価格異常、ドローダウン・ポジション上限を監視
- MonitoringEngine
  - 上記モニタ群を束ねてポーリングし、KillSwitch / AlertManager を使って通知・停止指示を行う
- OrderManager / Reconciler
  - 注文のライフサイクル管理と起動時のリコンシリエーション（再同期）
- portfolio.* / research.* / ai.*
  - ポートフォリオ構築、ファクター算出、ニュース NLP / レジーム判定など研究・付随処理

よくある運用コマンド（例）
------------------------
- 監視開始（デーモン化等は運用に合わせて systemd 等を使う）
  - KABUSYS_ENV=live python -m kabusys.run_monitoring &

- Execution 起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（ローカル）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
本 README ではライセンス情報は含めていません。実プロジェクトでは LICENSE ファイルを追加し、貢献ガイド（CONTRIBUTING.md）やコードスタイルを整備してください。

問い合わせ
----------
実装上の不明点や運用に関する質問があれば、ソースの該当モジュール（例: monitoring/*.py, ai/*.py）を参照してください。ソースには各関数・クラスに詳しい docstring が書かれています。

以上。