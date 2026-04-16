KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python コードベースです。本リポジトリは以下の主要機能を含みます。

- 注文発行・状態管理（Execution 層）
- 再起動時リコンシリエーション（Reconciler）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- ファクター計算・特徴量探索（Research / DuckDB ベース）
- ニュース NLP による銘柄別センチメント評価（OpenAI API）
- 市場レジーム判定（MA + マクロニュース + LLM）
- 運用監視（System / Trade / Risk Monitor）、LINE 通知、kill switch
- 監視データ向け Streamlit ダッシュボード、Paper Trading の検証レポート生成

設計上のポイント
- DuckDB / SQLite をデータ格納に利用（prices_daily, raw_financials, ai_scores, monitoring DB 等）
- 環境変数と .env(.env.local) による設定（Settings モジュール）
- Paper Trading（KABUSYS_ENV=paper_trading）の際はブローカーをモックして本番 DB と分離
- OpenAI 呼び出しにはリトライ・バリデーション等のフェイルセーフ実装
- 自動ロードされる .env のパーサは export / クォート / コメント等に対応

主な機能一覧
----------------
- Execution（起動スクリプト: run_execution.py）
  - Broker クライアント生成（実ブローカー / モック）
  - OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動
  - Paper Trading 時は paper_trading.db に記録し本番 DB と分離

- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor: CPU/MEM/Disk、データ鮮度、実行プロセス PID チェック
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数上限監視（kill switch と連携）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 定期ポーリング（MONITOR_POLL_INTERVAL で間隔指定）

- AI / News
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores に書き込み
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュース（LLM）で市場レジーム判定

- Portfolio
  - 候補選定（select_candidates）、等重/スコア重み付け（calc_equal_weights/calc_score_weights）
  - リスク調整（apply_sector_cap, calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- Research
  - ファクター計算（momentum/volatility/value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー等

- Tools
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report
  - Streamlit ダッシュボード: monitoring/streamlit_dashboard.py

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.9+（使用されるライブラリの互換性に依存）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須 (コード参照):
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれでインストールしてください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 主要な環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN — （必須）J-Quants トークン
     - KABU_API_PASSWORD — （必須）kabu API パスワード
     - OPENAI_API_KEY — OpenAI API キー（news, regime で使用）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / MONITOR_POLL_INTERVAL など（下記参照）
   - .env のパースは export プレフィックスやクォート、コメント等に対応しています。

使い方（主要コマンド）
--------------------

- 監視ループを起動
  - デフォルト: MONITOR は production sqlite_path を使う（run_monitoring は KABUSYS_ENV に依らず本番 sqlite を参照する点に注意）
  - 実行:
    - KABUSYS_ENV=development python -m kabusys.run_monitoring
    - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - Ctrl+C、またはプロジェクトルート data/stop_requested.flag を作成するとループ終了

- 実行エンジンを起動（ExecutionEngine）
  - Paper Trading モード（MockBroker）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB と完全に分離されます
  - Live / Development モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると実行中のエンジンに停止シグナルが送られます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視 DB の可視化）
  - 起動コマンド（リポジトリ直下から）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます（存在しない場合は MonitoringEngine を先に起動してください）。

設定（主要）
-------------
- Settings（kabusys.config.Settings）で多くの設定を環境変数経由で取得します。主なプロパティ:
  - env, is_live, is_paper, is_dev
  - sqlite_path（デフォルト: data/monitoring.db）
  - paper_sqlite_path（デフォルト: data/paper_trading.db）
  - duckdb_path（デフォルト: data/kabusys.duckdb）
  - pid_file_path（デフォルト: data/execution.pid）
  - kill_flag_path（デフォルト: data/kill.flag）
  - PAPER_FILL_MODE（instant|partial|never|reject）
  - CPU/MEM/DISK 閾値（CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT）
  - LOG_LEVEL

運用上の注意
-------------
- run_monitoring.py は監視用 DB に対して init_monitoring_db を実行しテーブルを準備します。
- run_monitoring は Monitoring 用 sqlite を常に production（Settings.sqlite_path）を参照します（KABUSYS_ENV に依らない）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して DB を分離します。
- KillSwitch（kill.flag）の書き込みにより ExecutionEngine に停止を促せます。kill.flag をクリアするメソッドも用意されています（KillSwitch.clear）。
- OpenAI の呼び出し（news_nlp / regime_detector）は API キー必須。API の失敗時は安全側のフォールバックが適用され、例外を上位に投げない実装が基本ですが、キー未設定時は ValueError となります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / .env 管理（Settings）
- run_monitoring.py            — Monitoring ポーリング起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                — ニュースセンチメント（OpenAI）
  - regime_detector.py         — 市場レジーム判定（MA + マクロニュース + LLM）
- monitoring/
  - monitoring_db.py           — SQLite テーブル作成 / 永続化層
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
  - (その他 ExecutionEngine / broker 周りの実装)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py

重要ファイル・パス（デフォルト）
- data/monitoring.db            — 監視 SQLite DB（Settings.sqlite_path）
- data/paper_trading.db         — Paper Trading 用 SQLite（Settings.paper_sqlite_path）
- data/kabusys.duckdb           — DuckDB ファイル（Settings.duckdb_path）
- data/execution.pid            — ExecutionEngine の PID ファイル（Settings.pid_file_path）
- data/stop_requested.flag      — run_* スクリプトの即時停止用フラグ（存在すると停止）
- data/kill.flag                — KillSwitch 発動用フラグ（ExecutionEngine 停止シグナル）

サンプル .env（最低限）
---------------------
# KABUSYS 環境
KABUSYS_ENV=development

# API トークン（実運用では安全に管理してください）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

# DB パス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

その他・貢献
-------------
- テストや CI に関するコードは本断片に含まれていません。ユニットテストや linters の導入を推奨します。
- OpenAI / 外部 API を利用する箇所は外部呼び出しのモック化を行いやすい設計になっています（_call_openai_api を patch する等）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期バージョン）
- ライセンス情報はリポジトリの LICENSE ファイルに従ってください（本コード断片には含まれていません）。

お問い合わせ
------------
実装・運用に関する質問や改善提案があれば、リポジトリの Issue に記載してください。