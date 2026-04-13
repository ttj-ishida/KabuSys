README
======

概要
----
KabuSys は日本株向けの自動売買システム（ミニマル実装）です。本リポジトリはトレード実行・モニタリング・ポートフォリオ構築・リサーチ・AI ニューススコアリング等の主要コンポーネントを含むモジュール群を提供します。コードはローカル SQLite / DuckDB をデータ永続化に利用し、OpenAI を使ったニュースセンチメントやレジーム判定の機能も備えています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）／注文管理（OrderManager）／リコンシリエーション（Reconciler）
- 監視フレームワーク（MonitoringEngine）
  - システム状態監視（CPU/メモリ/ディスク/プロセス生存）
  - 注文滞留・約定異常監視
  - ドローダウン／ポジション上限監視（KillSwitch による停止フラグ出力）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（監視表示）
- ポートフォリオ構築ライブラリ（候補選定、重み計算、リスク調整、ポジションサイジング）
- リサーチモジュール（ファクター計算、特徴量探索、IC 計算等）
- AI モジュール
  - ニュースを OpenAI に送りセンチメントを計算して ai_scores に保存（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール: Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）

前提 / 必要環境
---------------
- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
  - そのほかプロジェクトで利用する依存（pip でインストール可能）
- OpenAI API を使う機能は OPENAI_API_KEY が必要
- ローカルディスクに data/ ディレクトリへ書き込み可能であること

インストール（例）
-----------------
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を置くと自動で読み込まれる
   - .env は .git または pyproject.toml をプロジェクトルート判定に使用するため、リポジトリルートに置いてください。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（代表例）
---------------------
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須になる箇所あり）
- KABU_API_PASSWORD: kabuステーション API 用（必須になる箇所あり）
- OPENAI_API_KEY: OpenAI 呼び出し用 API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の成行/部分約定の挙動（instant|partial|never|reject。デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" でクリア）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）。0 以下は無効
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 送信用

セットアップ手順（簡易）
---------------------
1. .env を準備（必要な環境変数を設定）
   - .env.example があれば参照してください（本リポジトリには例ファイルは含めていません）。
2. data/ ディレクトリ作成:
   - mkdir -p data
3. DuckDB / SQLite DB 用ファイルパスを env で指定（省略可）
4. 必要な API キー（OpenAI 等）を設定

起動・使い方
------------

モニタ（Monitoring）を常時稼働させる
- デフォルトのポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で変更可）
- 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）
- 起動例:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

実行エンジン（Execution）
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（data/paper_trading.db）へ記録して本番 DB と分離します。
- 起動例:
  - python -m kabusys.run_execution
  - paper_trading モード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

Streamlit ダッシュボード
- Monitoring DB を読み取り専用で表示
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート（ツール）
- data/paper_trading.db の集計を人が読めるレポートとして標準出力に出す
- 起動例:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI（ニュースセンチメント / レジーム判定）
- OpenAI API キー (OPENAI_API_KEY) を設定して使用
- プログラムから呼ぶ例:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  # ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key="...")

注意点・挙動
-------------
- Settings（kabusys.config）は .env/.env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_monitoring は Monitoring 用 DB に対して init_monitoring_db() を行い必要テーブルを作成します（冪等）。
- run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（set_process_priority）。権限により失敗する場合はログに警告が出ます。
- Monitoring は KABUSYS_ENV に関係なく設定された sqlite_path（本番パス）を使用します。Paper Trading の分離は run_execution が PAPER_TRADING_SQLITE_PATH を使う点に注意してください。
- OpenAI へのリクエストはリトライとバックオフの仕組みを持ち、失敗時はフェイルセーフ（多くのケースで 0.0 にフォールバックなど）で継続しますが、API キー未設定時は例外を送出します（明示的に渡すことも可能）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- run_monitoring.py              — SystemMonitor をポーリングで回す起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                   — ニュースを OpenAI に投げてスコア化
  - regime_detector.py            — 市場レジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py              — SQLite ベースの監視ログ永続化層
  - system_monitor.py             — システム状態 / データ鮮度監視
  - trade_monitor.py              — 注文滞留 / 約定価格異常監視
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - kill_switch.py                — kill.flag 管理
  - alert_manager.py              — LINE 送信ユーティリティ
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py        — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - risk_adjustment.py            — セクター上限 / レジーム乗数等
  - position_sizing.py            — 株数計算・キャップ・単元丸め
  - __init__.py

- research/
  - factor_research.py            — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - __init__.py

- execution/
  - order_manager.py              — Order 管理 API（state machine）
  - reconciler.py                 — 再起動時の同期（リコンシリエーション）
  - (その他 execution 関連モジュール: broker_api等 ／ 実装の一部は省略)

- tools/
  - paper_verification_report.py  — Paper Trading レポート生成 CLI
  - __init__.py

- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

ドキュメント・設計メモ
--------------------
- 各モジュールの docstring に設計思想や注意点が細かく書かれています。実運用前に Monitoring, KillSwitch, Risk 設定（閾値等）を精査してください。
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db() に定義されています。マイグレーションは一部（列追加等）がコード内で扱われています。
- Paper Trading（シミュレーション）は本番 DB と完全に分離するよう設計されています。実際に本番ブローカーを接続する前に paper_trading モードで挙動確認を行ってください。

貢献・開発
----------
- 新機能追加やバグ修正は PR を歓迎します。テストがあれば合わせて追加してください。
- 自動化 / CI / デプロイの仕組みはこの README の範囲には含めていません。必要に応じてワークフローを整備してください。

ライセンス
----------
- 特に記載がない場合はリポジトリ内のライセンスファイルに従ってください。

以上。運用・開発で不明点があれば、対象モジュールの docstring を参照または質問してください。