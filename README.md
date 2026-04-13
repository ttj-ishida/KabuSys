KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージ群です。  
主な目的は以下です。

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築・サイズ計算（portfolio）
- 注文発行・ExecutionEngine による発注処理（execution）
- 監視（MonitoringEngine）によるシステム状態・注文監視、LINE 通知、kill flag 発行（monitoring）
- Paper Trading 用の検証レポート生成ツール（tools）
- ニュース NLP（OpenAI）を使ったセンチメント集計と市場レジーム判定（ai）

このリポジトリは純粋関数群（ポートフォリオ算出等）や DB 永続化レイヤ、Execution の補助ユーティリティ群を提供します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレードを KABUSYS_ENV によって切替可能
  - paper_trading 時は MockBrokerClient を利用し、data/paper_trading.db に記録（本番 DB と明確分離）
  - 発注前後のリコンシリエーション（Reconciler）対応
  - RiskManager（ポジション上限・投下率等）を組み込んだ発注管理
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検知
  - RiskMonitor：ドローダウン監視・ポジション上限検知、ダッシュボード更新
  - MonitoringEngine：各種 Monitor を束ねてポーリング、AlertManager 経由で LINE に通知
  - kill.flag を書く KillSwitch による ExecutionEngine 停止シグナル
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出、ai_scores に書込
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定を行い、market_regime に書込
  - API 呼び出しはリトライ・フェイルセーフ設計
- 研究・ファクター（research）
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials からファクターを算出
  - feature_exploration：将来リターン計算・IC（情報係数）計算・統計サマリー
- ポートフォリオ（portfolio）
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ・レジーム乗数）、株数決定（単元丸め・aggregate cap）
- ユーティリティ
  - 設定管理（kabusys.config.Settings）：.env 自動ロード（プロジェクトルート基準）・環境変数取り扱い
  - process_priority ユーティリティ：Windows / POSIX に対応した優先度・CPU affinity 設定
  - monitoring_db：監視用 SQLite スキーマ生成・ラッパー（MonitoringDB）

セットアップ
-----------
前提
- Python 3.10+（typing の | 演算子等を使用しているため）
- SQLite（Python 標準搭載）、DuckDB、psutil、requests、openai、streamlit 等の依存ライブラリ

例: 仮想環境を作成して依存をインストールする手順（例示）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. 開発インストール（任意）
   - pip install -e .

環境変数 / .env
- 本パッケージは .env / .env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（Settings に定義されている項目）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時に必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（paper_trading DB path、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB path、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB path、デフォルト: data/monitoring.db）
- PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（kill.flag path、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアする場合は "1"）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- LOG_LEVEL（DEBUG|INFO|...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き、デフォルト 60）

使い方（主要コマンド）
---------------------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring はプロセス優先度を "high" に設定し、MonitoringDB（SQLite）を初期化して SystemMonitor のポーリングを開始します

- ExecutionEngine を起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い data/paper_trading.db を利用（本番 DB と完全分離）
  - 起動時に Reconciler による注文・ポジション照合が実行されます

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、システム状態・ポジション・最近の注文・リスクログを表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db

- AI 機能（プログラムから利用）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # api_key を渡すか OPENAI_API_KEY を環境変数で設定
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

主要ファイル・ディレクトリ構成
------------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py                (パッケージ定義, __version__)
  - config.py                  (Settings, .env 自動ロード)
  - run_monitoring.py          (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py           (ExecutionEngine 起動スクリプト)
  - utils/
    - __init__.py
    - process_priority.py      (プロセス優先度 / CPU affinity ユーティリティ)
  - monitoring/
    - __init__.py
    - monitoring_db.py         (SQLite スキーマ初期化 + MonitoringDB ラッパー)
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
    - (その他: broker_factory, execution_engine, order_repository 等が存在)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

（補足）
- DuckDB は prices_daily / raw_financials / raw_news 等の分析用テーブルを想定しています。これらのテーブルは本パッケージ外で ETL して用意する想定です（kabusys.data.pipeline など別モジュールで取得実装が参照されています）。
- monitoring_db.init_monitoring_db(conn) は監視用 SQLite のテーブルを作成し、必要なマイグレーション（カラム追記）を行います。MonitoringDB クラスはログ追記・ダッシュボード upsert 等の便利メソッドを提供します。

運用上の注意
------------
- 本プロジェクトは実際の発注・資金移動を伴う可能性があります。live 環境での稼働前に paper_trading で十分にテストしてください。
- OpenAI API キーの漏洩に注意し、必要最小限の権限で管理してください。
- run_monitoring / run_execution 起動時にプロセス優先度設定を試みますが、権限不足で失敗する場合はログに警告を出して続行します。
- kill.flag の存在で ExecutionEngine を停止させる設計です。必要に応じて起動時に KILL_FLAG_CLEAR_ON_START=1 を使ってフラグを自動クリアできます（運用ポリシーに注意）。

ライセンス / 貢献
-----------------
本 README はコードベースに基づく概要と使い方の説明です。実装の詳細や拡張、バグ修正は Pull Request を歓迎します。

付録: よく使うコマンド例
-----------------------
- 監視起動（デフォルト 60s）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上です。必要であればセットアップ手順や env の雛形（.env.example）や運用チェックリストを追加で作成します。どの情報を優先して載せたいか教えてください。