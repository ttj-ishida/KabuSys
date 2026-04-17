KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ユーティリティ群をまとめた小規模フレームワークです。本コードベースは以下の主要機能群を含みます。

- 注文実行エンジン（ExecutionEngine）と関連コンポーネント（OrderManager / Reconciler / RiskManager 等）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイジング等）
- 研究（ファクター計算・特徴量探索）
- ニュース NLP / レジーム検出（OpenAI を利用したセンチメント評価）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主要な設計方針（抜粋）
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- 日次バッチ・LLM 呼び出しはフェイルセーフ（API失敗時はエラーを吸収して継続）
- .env / .env.local による設定の自動読み込み（必要に応じて無効化可能）

機能一覧
--------
- 実行関連
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - Broker クライアントの切替（本番 / paper_trading）
  - 再起動時のリコンシリエーション（Reconciler）
- 監視関連
  - SystemMonitor（CPU/Mem/Disk、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限、ダッシュボード更新）
  - KillSwitch（条件に応じて data/kill.flag を書き込み、Execution 停止トリガ）
  - MonitoringEngine（まとめてポーリング）
  - Streamlit ダッシュボード（読み取り専用で監視状況表示）
- ポートフォリオ
  - 候補選定、等重・スコア重み、セクター上限、ポジションサイズ計算
- リサーチ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン算出、IC（Spearman）計算、統計サマリー
- AI / ニュース
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector: MA200 とマクロセンチメントを合成して市場レジーム（bull/neutral/bear）を判定
- ツール
  - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py
  - Streamlit ダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py

前提・依存
----------
主要な Python ライブラリ（例）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- そのほか標準ライブラリ（sqlite3, threading, datetime, pathlib など）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートにする（.git または pyproject.toml が存在する場所がプロジェクトルートと判定されます）。

2. Python 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を使って依存管理してください。

4. 環境変数の設定
   - .env または .env.local に設定を記述できます。自動読み込みはデフォルトで有効です（プロジェクトルートが特定できる場合）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境 (development | paper_trading | live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須、J-Quants API 用）
- KABU_API_PASSWORD: （必須、kabuステーション API 用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- PAPER_FILL_MODE: Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, など多数（詳細は src/kabusys/config.py を参照）

使い方
------
実行系（ExecutionEngine）
- 起動（パッケージのルートから）
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py

- 特記事項
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録し、本番 DB と完全に分離します。
  - 起動時に data/kill.flag が存在する場合はエンジンは起動しません（停止フラグの保護）。
  - 実行中は data/execution.pid に PID を書きます。run_execution スクリプトは data/stop_requested.flag を監視して安全に停止します。

監視系（MonitoringEngine）
- 単独起動
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py

- ポーリング間隔の変更
  - 環境変数 MONITOR_POLL_INTERVAL に秒数をセット（デフォルト 60 秒）。
    - 例: export MONITOR_POLL_INTERVAL=30

- 停止
  - プロジェクトルート/data/stop_requested.flag を作成すると次回ループで停止します。

Streamlit ダッシュボード（読み取り専用）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB は読み取り専用で開かれます（URI mode=ro を使用）。

Paper Trading 検証レポート
- 単発レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

AI（ニュース・レジーム判定）
- 動作には OPENAI_API_KEY が必要です。キーが未設定の場合、score_news / score_regime は ValueError を投げます。
- LLM 呼び出しはリトライやフェイルセーフが組み込まれていますが、API 費用・レート制限に注意してください。

停止フラグ / キルフロー
- stop_requested.flag: run_monitoring / run_execution の外部停止要求（ファイル存在を監視して安全に停止）
  - ファイル位置（project_root/data/stop_requested.flag）
- kill.flag: KillSwitch が書き込む停止トリガ（ExecutionEngine に対して停止シグナルを与える目的）
  - ファイル位置（設定により変更可、Settings.kill_flag_path）
- execution.pid: ExecutionEngine の PID ファイル（path は Settings.pid_file_path）

DB とマイグレーション
- 監視用 SQLite（data/monitoring.db）には monitoring_db モジュールで必要テーブルを冪等に作成します。
- 古いスキーマに対して軽微なマイグレーション（列追加）を自動的に実行する処理があります（例: dashboard.peak_value, trade_logs.latency_ms）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI 連携）
  - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (BrokerFactory/Engine/OrderRepository 等 — 実装ファイル群)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

運用上の注意 / ベストプラクティス
--------------------------------
- 環境変数は .env/.env.local に保存できますが、機密情報（APIキー等）は適切に管理してください。
- Paper Trading と Live を混同しないでください。paper_trading モードは意図的に DB とブローカー実装を分離しています。
- OpenAI 等の外部 API 呼び出しはコストとレート制限に注意して使用してください。テスト時は API 呼び出し関数をモックする設計になっています。
- set_process_priority や CPU affinity 設定は OS 権限に依存します（psutil の権限エラーをハンドルしてスキップします）。

参考・実装ファイルの参照
-----------------------
- 設定の挙動や利用可能な環境変数は src/kabusys/config.py を参照してください。
- 監視テーブルのスキーマやログ書き込みは src/kabusys/monitoring/monitoring_db.py を参照してください。
- AI 関連のプロンプト設計やリトライ方針は src/kabusys/ai/news_nlp.py / regime_detector.py に記載されています。

ライセンス・貢献
----------------
本リポジトリ固有のライセンス情報や貢献ルールがある場合はプロジェクトルートに LICENSE / CONTRIBUTING.md を置いてください（このコードベースには含まれていません）。

以上。必要であればインストール用 requirements.txt や起動スクリプトの具体的な例（systemd ユニットファイル、Dockerfile など）を追記します。ご希望があれば追加します。