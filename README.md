README
=====

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした小規模なフレームワークです。  
主な機能には、注文の実行エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ、ニュースの NLP によるセンチメント評価などが含まれます。  
モジュールは可能な限り副作用を抑えた設計（DB 分離、純粋関数、フェイルセーフ）になっています。

主な特徴
--------
- Execution／Monitoring のランナー（run_execution / run_monitoring）を提供
  - KABUSYS_ENV による実行モード切替（development / paper_trading / live）
  - paper_trading モードではブローカーをモックし、paper 用 DB に記録して本番 DB と分離
- 監視機能
  - システム状態（CPU/Mem/Disk/プロセス）記録
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限の監視と kill.flag による安全停止
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボード（read-only）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・単元丸め・リスク調整）
- リサーチ / ファクター計算（DuckDB ベース）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン・IC 計算・統計サマリ
- ニュース NLP（OpenAI を使ったセンチメント集約）
  - 銘柄ごとのスコアを ai_scores テーブルに保存
  - レジーム判定モジュール（ETF ma200 とマクロニュースの合成）
- 各種ユーティリティ（プロセス優先度設定、.env 自動ロードなど）

セットアップ手順
---------------
前提:
- Python 3.10+ を推奨（typing の構文、future annotations を利用）
- SQLite は標準ライブラリで利用可能
- DuckDB を利用（duckdb パッケージ）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows では .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトをパッケージ化している場合は requirements.txt / pyproject.toml を利用してください）

3. 環境変数設定
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数例（.env に記載する例）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...                （ニュース NLP / レジーム判定で必要）
   - PAPER_FILL_MODE=instant | partial | never | reject
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - LINE_CHANNEL_ACCESS_TOKEN=...    （アラート用）
   - LINE_USER_ID=...                 （アラート用）

4. データディレクトリ作成
   - mkdir -p data

5. DB 初期化
   - run_monitoring / run_execution は起動時に必要な監視テーブルを（冪等に）作成します。
   - DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）は利用するデータパイプライン／ETL スクリプトで用意してください。

使い方
------
- 実行（Monitoring）
  - 簡易実行:
    - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループのポーリング間隔を秒単位で上書きできます（デフォルト: 60）。
    - 例: export MONITOR_POLL_INTERVAL=30

- 実行（Execution Engine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使って注文を記録します。
  - 起動中は data/execution.pid に PID が書かれ、外部から停止を指示する場合は data/stop_requested.flag を作成します。

- Streamlit ダッシュボード（監視の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトの DB パスは data/monitoring.db。引数 --db で指定可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

- ニュース NLP / レジーム判定（プログラム的に利用）
  - OpenAI の API キーが必要です（OPENAI_API_KEY）。
  - 例: from kabusys.ai import score_news; score_news(conn, target_date, api_key=...)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime

- Kill / Stop 操作
  - Execution 停止指示: data/kill.flag を作成すると KillSwitch が動作して安全停止シグナルを出します（Monitoring が検出して Execution に通知）。
  - 手動で停止したい場合は data/stop_requested.flag を作成して run_* スクリプトを終了させます。
  - kill.flag をクリアするにはファイルを削除（rm data/kill.flag）してください。

運用上の注意
------------
- Monitoring は常に本番の sqlite_path を使って監視テーブルを記録します（KABUSYS_ENV に依存しない）。
- Execution は paper_trading モード時に paper 用 DB を使用して本番 DB と完全分離します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。見つからない場合は自動ロードをスキップします。
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API キーの管理とコストには注意してください。
- process priority と CPU affinity の設定はプラットフォーム依存で、設定に失敗してもログ警告で安全にスキップされます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                            — 環境変数/.env 管理
- run_monitoring.py                    — Monitoring のループ起動スクリプト
- run_execution.py                     — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                         — ニュースの LLM センチメント評価
  - regime_detector.py                  — 市場レジーム判定（MA200 + マクロ NLP）

- monitoring/
  - __init__.py
  - monitoring_db.py                    — SQLite による監視ログ永続化
  - system_monitor.py                   — システム状態 / データ鮮度監視
  - trade_monitor.py                    — 滞留注文 / 約定異常監視
  - risk_monitor.py                     — ドローダウン / ポジション上限監視
  - kill_switch.py                       — 停止フラグ管理
  - alert_manager.py                    — LINE 通知
  - monitoring_engine.py                — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py              — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...（ブローカー周り・Engine 実装はここに置かれています）

- portfolio/
  - portfolio_builder.py                — 候補選定・重み付け
  - position_sizing.py                  — 株数算出・単元丸め・資金配分
  - risk_adjustment.py                  — セクター上限・レジーム乗数

- research/
  - factor_research.py                  — ファクター計算（momentum/value/volatility）
  - feature_exploration.py              — 将来リターン / IC / 統計

- tools/
  - __init__.py
  - paper_verification_report.py        — Paper Trading 検証レポート生成スクリプト

- utils/
  - __init__.py
  - process_priority.py                 — プロセス優先度 / CPU affinity ヘルパー

補足
----
- DB スキーマ（prices_daily / raw_financials / raw_news など）は別 ETL / データ取得パイプラインで用意する想定です（DuckDB を用いる設計）。
- 監視テーブル（system_status / trade_logs / positions / risk_logs / dashboard）は init_monitoring_db() により自動作成・マイグレーションされます。
- 実運用では KABUSYS_ENV を正しく設定し（特に live モードでは注意）、ログレベルやしきい値（Settings の CPU_THRESHOLD_PCT 等）を調整してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報はリポジトリのトップレベルに含めてください（ここには記載していません）。

問題報告 / 貢献
---------------
- バグ報告・改善提案はリポジトリの issue にお願いします。README を参照して環境や実行ログを添えてください。

以上。必要があれば各コマンドの具体例や .env.example を作成します。