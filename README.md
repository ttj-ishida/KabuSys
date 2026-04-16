README.md

KabuSys — 日本株自動売買システム (簡易ドキュメント)
================

概要
----
KabuSys は日本株の自動売買・検証・監視を目的としたモジュール群です。
コードベースは取引実行（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、
ポートフォリオ構築、ファクター研究、ニュース NLP（OpenAI を用いたセンチメント）、および運用・検証ツールを含みます。

主な特徴
-------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を環境変数で切替（paper_trading 時は MockBrokerClient と別 DB を使用）
  - 起動時に自動リコンシリエーション（Reconciler）で注文・ポジション同期
- Monitoring（run_monitoring.py）
  - システム資源・データ鮮度・注文異常・リスク監視をポーリング
  - 監視ログは SQLite（data/monitoring.db）に永続化
  - kill.flag による ExecutionEngine 停止シグナル出力機能（KillSwitch）
- 監視ダッシュボード（streamlit）
- Paper Trading 検証レポート生成ツール（paper_verification_report）
- AI モジュール
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとにセンチメントを ai_scores に保存
  - regime_detector: 市場レジーム判定 (ma200 + マクロセンチメント)
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ算出・セクター制限）
- 研究モジュール（ファクター計算、特徴量探索、IC 計算、統計サマリ）

必要条件
--------
- Python 3.9+
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- （任意）.env ファイルの読み込みを行うために .env/.env.local をプロジェクトルートに配置可能

セットアップ
----------
1. リポジトリをクローンしてワークディレクトリに移動。
2. 仮想環境の作成・有効化（推奨）。
3. 必要パッケージをインストール（例）:
   pip install duckdb psutil requests openai streamlit
4. data ディレクトリ等が必要なら作成:
   mkdir -p data
5. 環境変数 / .env を設定（下の「環境変数」参照）。

環境変数（代表例）
-----------------
プロジェクトは .env / .env.local または OS 環境変数から設定を読み込みます（デフォルトで自動読み込み）。
自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（キーとデフォルト）:
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション接続パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用 LINE 設定（未設定なら送信はスキップ）
- PAPER_FILL_MODE: paper_trading 時の約定モード (instant | partial | never | reject)（デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルト data/execution.pid / data/kill.flag
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- その他: CPU/MEM/DISK 閾値等（Settings クラスを参照）

簡易 .env.example
-----------------
（参考: プロジェクトルートに .env を置く）
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant

使い方
------

1) 監視プロセスを起動 (Monitoring)
- デフォルトで production の sqlite_path を使って監視ログを書きます（KABUSYS_ENV に依らず）。
- 起動:
  python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring のループは検知して終了します。

2) 実行エンジンを起動 (ExecutionEngine)
- paper_trading モードでは paper_sqlite_path に書き込み、本番と分離されます。
- 起動:
  KABUSYS_ENV=development python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 実行中の停止:
  - data/stop_requested.flag を作成すると実行エンジンを停止させる挙動を持ちます。
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
- PID 管理:
  - 実行時に data/execution.pid（デフォルト）へ PID を書きます。SystemMonitor はこの PID を監視し stale（プロセス不在）を検出します。

3) Streamlit ダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で SQLite を開くため、監視プロセスと同時に安全に閲覧できます。

4) Paper Trading 検証レポート
- 期間を指定してレポートを出力:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを直接指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI モジュール（プログラムから呼び出す）
- OpenAI API キーを設定してから関数を呼ぶ:
  from kabusys.ai.news_nlp import score_news
  # duckdb_conn は DuckDB 接続
  score_news(duckdb_conn, target_date, api_key="...")

- 市場レジーム:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

注意点 / 運用上のポイント
------------------------
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング。0 以下の値は無効扱い（デフォルト 60 秒）。
- Monitoring は環境にかかわらず本番 sqlite_path を参照します（監視ログは本番側に記録する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使い DB を完全に分離します。
- AI 関連機能は OpenAI の課金が発生するため注意。API 呼び出しはリトライ・バックオフを備えていますが失敗時はフォールバックして継続する設計です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）から行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- LINE 通知は channel token / user id が未設定のときはログ出力のみで実際の送信は行いません。
- monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成 / 必要なカラム追加を行います（軽微なマイグレーションを自動適用）。

主なファイル・ディレクトリ構成
----------------------------
src/kabusys/
- __init__.py                     — パッケージ定義
- config.py                       — 環境変数 / Settings 管理（.env 自動ロード含む）
- run_monitoring.py               — Monitoring を起動するスクリプト
- run_execution.py                — ExecutionEngine を起動するスクリプト

src/kabusys/monitoring/
- monitoring_db.py                — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py               — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py                — 注文滞留・約定異常検出
- risk_monitor.py                 — ドローダウン・ポジション上限監視
- kill_switch.py                  — kill.flag 作成（Execution 停止シグナル）
- alert_manager.py                — LINE push 通知（クールダウン管理）
- monitoring_engine.py            — 各 Monitor を統合してポーリング
- streamlit_dashboard.py          — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py, reconciler.py, ... — 発注／リコン周りの実装（OrderRepository 等は別ファイル）

src/kabusys/portfolio/
- portfolio_builder.py             — 候補選定・重み計算
- position_sizing.py               — 株数計算、単元丸め、集約キャップ
- risk_adjustment.py               — セクターキャップ、レジーム乗数

src/kabusys/research/
- factor_research.py               — Momentum/Value/Volatility 等のファクター計算（DuckDB 再利用）
- feature_exploration.py           — 将来リターン / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py                      — ニュース記事の LLM スコアリング（ai_scores 書き込み）
- regime_detector.py               — 市場レジーム判定（ma200 + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py     — Paper Trading 検証レポート

data/
- monitoring.db (default)          — 監視用 SQLite（デフォルトパス）
- paper_trading.db (default)       — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
- kabusys.duckdb (default)         — DuckDB ファイル
- execution.pid                     — ExecutionEngine の PID 管理
- kill.flag / stop_requested.flag   — 制御フラグファイル

開発／拡張メモ
--------------
- DuckDB 接続を渡す設計のため、研究モジュールは本番取引とは独立して動作します（安全）。
- OpenAI 呼び出しはモジュール内で抽象化しており、テスト時は _call_openai_api をモックできます。
- monitoring_db.init_monitoring_db は軽微なスキーママイグレーション（カラム追加）を行います。
- process 優先度や CPU affinity 設定は utils/process_priority.py で OS 間差異を吸収しています（psutil に依存）。

ライセンス / その他
-------------------
本リポジトリのライセンス情報や運用上の注意（実際のブローカー接続や資金管理に関する責任）は別途 README / LICENSE を参照してください。

必要なら、この README にサンプル .env.example、起動スクリプトの systemd ユニット例、テストの実行方法などを追加作成します。要望があれば教えてください。